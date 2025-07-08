# backend.py

import time
import pyvisa
import ctypes

def init_instrument(resource: str, terminal: int, max_limit_ma: float, timeout_ms: int = 5000):
    """
    Initialize the DC2200: reset, set the current limit, and select the LED terminal (1 or 2).
    Also disable Windows Quick-Edit so mouse clicks won't pause the console.
    Returns the VISA instrument handle.
    """
    # ————— Disable Quick-Edit Mode on Windows console —————
    STD_INPUT_HANDLE      = -10
    ENABLE_QUICK_EDIT     = 0x0040
    ENABLE_EXTENDED_FLAGS = 0x0080

    kernel32 = ctypes.windll.kernel32
    hStdin   = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    mode     = ctypes.c_uint()
    # get current console mode
    kernel32.GetConsoleMode(hStdin, ctypes.byref(mode))
    # clear QUICK_EDIT bit & ensure EXTENDED_FLAGS is set
    new_mode = (mode.value & ~ENABLE_QUICK_EDIT) | ENABLE_EXTENDED_FLAGS
    kernel32.SetConsoleMode(hStdin, new_mode)
    # ————————————————————————————————————————————————

    rm   = pyvisa.ResourceManager()
    inst = rm.open_resource(resource)
    inst.timeout = timeout_ms
    inst.write('*RST')
    # Set safety current limit
    inst.write(f'SOURce1:CURRent:LIMIt:AMPLitude {max_limit_ma/1000}')
    # Select LED terminal
    inst.write(f'OUTPut1:TERMinal {terminal}')
    return inst


def configure_pulse_mode(inst, max_limit_ma: float):
    """
    Switch the controller into Pulse modulation mode with the given global limit.
    """
    inst.write('SOURce1:MODe PULS')
    inst.write(f'SOURce1:CURRent:LIMIt:AMPLitude {max_limit_ma/1000}')


def set_pulse_parameters(inst, on_time: float, off_time: float,
                         max_limit_ma: float, current_ma: float):
    """
    Program one pulse at current_ma (mA) with specified ON/OFF durations.
    """
    pct = (current_ma / max_limit_ma) * 100
    inst.write(f'SOURce1:PULSe:BRIGhtness:LEVel:AMPLitude {pct}')
    inst.write(f'SOURce1:PULSe:ONTime {on_time}')
    inst.write(f'SOURce1:PULSe:OFFTime {off_time}')
    inst.write('SOURce1:PULSe:COUNt 1')


def fire_pulse(inst):
    """
    Trigger the programmed pulse (count=1).
    """
    inst.write('OUTPut1:STATe ON')


def measure(inst):
    """
    Read the DC current (in mA) and voltage (in V) from the active terminal.
    """
    i = float(inst.query('MEASure:CURRent:DC?')) * 1000
    v = float(inst.query('MEASure:VOLTage:DC?'))
    return i, v


def turn_off(inst):
    """
    Ensure the LED output is turned off.
    """
    inst.write('OUTPut1:STATe OFF')


def cleanup(inst):
    """
    Safely turn the LED off and close the VISA session.
    """
    try:
        turn_off(inst)
    except Exception:
        pass
    try:
        inst.session.close()
    except Exception:
        pass


def run_sweep(inst,
              initial_countdown: int,
              on_time: int,
              off_time: int,
              currents_ma: list,
              max_limit_ma: float):
    """
    Runs a full pulse sequence:
     - initial countdown
     - for each current in currents_ma:
         * program & fire a single pulse
         * wait exactly 1s, then measure
         * wait remaining (on_time - 1)s so total ON = on_time
         * turn LED off, query & print OFF status
         * wait exactly off_time seconds
    Catches KeyboardInterrupt to turn off LED immediately.
    """
    # Initial countdown
    for t in range(initial_countdown, 0, -1):
        print(f'Starting in {t:2d}s…', end='\r')
        time.sleep(1)
    print(' ' * 40, end='\r')

    try:
        for idx, curr in enumerate(currents_ma, start=1):
            print(f'\nPulse {idx}/{len(currents_ma)} → {curr} mA')
            # Program the pulse
            set_pulse_parameters(inst, on_time, off_time, max_limit_ma, curr)
            fire_pulse(inst)

            # 1) Wait 1s and measure
            time.sleep(1)
            meas_I, meas_V = measure(inst)
            print(f'  ☑ [1s] {meas_I:.1f} mA | {meas_V:.2f} V')

            # 2) Wait remaining ON time (on_time - 1)
            for remaining in range(on_time - 1, 0, -1):
                print(f'  ▶ ON remaining {remaining}s', end='\r')
                time.sleep(1)
            print(' ' * 40, end='\r')

            # 3) Turn off and report status
            turn_off(inst)
            status = inst.query('OUTPut1:STATe?').strip()
            print(f'  ▶ LED OFF (STATe?={status})')

            # 4) OFF-phase countdown
            for remaining in range(off_time, 0, -1):
                print(f'  ▶ OFF remaining {remaining}s', end='\r')
                time.sleep(1)
            print(' ' * 40, end='\r')

    except KeyboardInterrupt:
        print('\n⚠️  Interrupted! Turning LED off…')
        turn_off(inst)
        status = inst.query('OUTPut1:STATe?').strip()
        print(f'  ▶ LED OFF status={status}')
        return  # exit immediately
