# Firmware

RP2040 firmware for the standard Seeed XIAO RP2040. It's built with PlatformIO and the [Arduino-Pico](https://github.com/earlephilhower/arduino-pico) core.

| File | What |
|---|---|
| `src/main.cpp` | Hardware side: ADC sampling, GPIO output, USB serial commands, watchdog |
| `include/swc_logic.h` | Portable decoder and timing logic. The host tests and the SPICE co-simulation use this same file. |
| `tests/test_logic.cpp`, `tests/check_contract.py` | Host unit tests, plus a check of the firmware's pin and mask tables against `hardware/output_commands.json` and `design_intent.json` |
| `releases/*.uf2` | Prebuilt images and their SHA-256 hashes (`validation.json`) |

## Two builds

| Build | Default behaviour |
|---|---|
| **vehicle** ([`tacoma-swc-vehicle.uf2`](releases/tacoma-swc-vehicle.uf2)) | Decodes the wheel buttons. It starts once both lines have read *released* for 100 ms, so powering up with a button held does nothing. |
| **bench** ([`tacoma-swc-bench.uf2`](releases/tacoma-swc-bench.uf2)) | Ignores the wheel. A command typed over USB serial gives one 300 ms pulse on that output, then releases. |

Either build switches to the other mode if you send it `vehicle` or `bench` over USB. That lasts until the next reset; nothing is stored.

## Loading

1. **Pull the JP1 shunt** on the carrier before plugging in USB.
2. Hold the XIAO's **BOOT** button while you plug in USB. An `RPI-RP2` drive appears.
3. Copy the UF2 file onto it. The XIAO restarts and runs it.
4. Unplug USB, then refit JP1 for use in the truck.

## USB serial

115,200 baud, with newline or CRLF line endings.

| Command | Does |
|---|---|
| `help` | Lists the commands |
| `status` | Mode, raw SW1/SW2 ADC counts, current output, uptime, boots since power-on, and the last reset cause |
| `bench` / `vehicle` | Switches mode (and releases) |
| `stop` or `release` | Releases all outputs |
| `volume_down`, `volume_up`, `source`, `seek_up`, `seek_down`, `phone`, `mute` | In bench mode: one 300 ms pulse. A new command during a pulse is rejected. |

After loading a UF2, `reset=watchdog-force` is normal. Unplugging USB during a bench pulse ends it.

### Bench test with the radio

1. Pull JP1 and leave ACC disconnected; USB powers the XIAO.
2. Power the radio separately.
3. Connect J1 pin 9 (or TP3) to the radio's SWRC+ (3.5 mm tip) and J1 pin 10 (or TP4) to SWRC GND.
4. Send each command and watch the radio respond. Don't put an ohmmeter across the outputs while the radio is connected.

### Checking the wheel bands on the bench

1. Send `vehicle`, with both inputs open, and wait 100 ms.
2. Put a resistor from SW1 or SW2 (J1 pin 4 or 8) to GND (pin 6).
3. Send `status`, and check that the right output turns on.
4. Release between tests.

Use 0, 330, 1000 and 3100 Ω on SW1, and 0, 330 and 1000 Ω on SW2.

## Decoding

| ADC count (12-bit, inclusive) | Meaning | SW1 | SW2 |
|---|---|---|---|
| 0–60 | near 0 Ω | Seek + | Mode |
| 340–630 | ~330 Ω | Seek − | Hang Up → Mic Mute |
| 930–1390 | ~1 kΩ | Volume + | Answer → Phone |
| 1830–2530 | ~3.1 kΩ | Volume − | ignored |
| 3160–4095 | released | | |
| anything else | invalid | | |

The bands come from simulating the input circuit across part tolerances (see [docs/interface.md](../docs/interface.md)). With the board idle, the inputs read about 4037.

**Timing**
- **Sampling.** Both lines are sampled every ~2 ms. The first conversion after switching ADC channels is thrown away.
- **Press.** A press must read the same valid band for 20 ms. Release happens on the next sample.
- **Settling.** Before a press is accepted, a reading in a gap gets up to 6 ms to settle through the RC filter.

**Lockouts.** All of these release the output and wait for 100 ms of idle before decoding again:
- an invalid reading that persists
- both lines active at once
- going straight from one button to another
- holding a button longer than 10 s

**Outputs.** Every change clears GP0–GP4, waits 20 µs (`busy_wait_us_32`), then sets the new mask in one register write. Paired resistors therefore switch on together.

**Power.** The XIAO runs one core at 50 MHz. The user LEDs are off, and the loop sleeps between samples. A 1 s watchdog resets a stalled loop.

The output GPIOs are, in order of bit: GP0 = 47 Ω, GP1 = 191 Ω, GP2 = 390 Ω, GP3 = 2 kΩ, GP4 = 1 kΩ. The inputs are SW1 = GP26, SW2 = GP27.

## Building

```sh
pio run -e vehicle      # .pio/build/vehicle/firmware.uf2
pio run -e bench        # .pio/build/bench/firmware.uf2
```

The platform is pinned to a specific commit in `platformio.ini`. The release images were built with Arduino-Pico `fd65f6d4`.

## Tests

From this directory:

```sh
c++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -I include tests/test_logic.cpp -o /tmp/swc-test && /tmp/swc-test
python3 tests/check_contract.py
```

The tests cover:
- every boundary between bands, and all 65,536 possible ADC readings
- timing for all seven commands
- debounce, lockout and re-arm
- disconnects and `millis()` rollover

`hardware/simulation/check_firmware_integration.py` goes further. It runs the same decoder against 3,024 simulated analog input waveforms.
