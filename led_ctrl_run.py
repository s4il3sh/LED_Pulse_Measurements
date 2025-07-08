# run_pulse.py

import time
from led_ctrl_backend import (
    init_instrument,
    configure_pulse_mode,
    run_sweep,
    cleanup
)

# === USER PARAMETERS ===
RESOURCE          = 'USB0::0x1313::0x80C8::M00811426::INSTR'
TERMINAL          = 2                 # LED head (1 or 2)
INITIAL_COUNTDOWN = 5                 # seconds before first sequence
ON_TIME           = 5                 # seconds LED stays ON
OFF_TIME          = 5                 # seconds LED stays OFF
START_LED_CURR_MA = 20                # start current (mA)
END_LED_CURR_MA   = 100               # end current (mA)
STEP_MA           = 20                # increment per pulse (mA)
MAX_LIMIT_MA      = 200               # safety current limit (mA)


def main():
    inst = init_instrument(RESOURCE, TERMINAL, MAX_LIMIT_MA)
    configure_pulse_mode(inst, MAX_LIMIT_MA)
    print(f'Connected: {inst.query("*IDN?").strip()}')
    print('Press Ctrl+C to interrupt the pulse sequence at any time.')

    try:
        while True:
            sweep_currents = list(range(START_LED_CURR_MA,
                                        END_LED_CURR_MA + 1,
                                        STEP_MA))
            run_sweep(inst,
                      INITIAL_COUNTDOWN,
                      ON_TIME,
                      OFF_TIME,
                      sweep_currents,
                      MAX_LIMIT_MA)

            # ask once after full sweep
            if input('\nRun another full pulse sequence? (y/n): ').strip().lower() not in ('y','yes'):
                break

    except KeyboardInterrupt:
        print('\n⚠️  Main interrupted! Turning LED off…')
    finally:
        cleanup(inst)
        print('Done!')


if __name__ == '__main__':
    main()