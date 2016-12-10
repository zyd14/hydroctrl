#!/usr/bin/env python3

import settings
import smbus


class PHTheory:
    """
    A set of pH electrode functions.

    Functions are derived from the following equation:
    V = Voffset - slope * R * T * LN10 / F * (pH - 7)
    """

    @staticmethod
    def ideal_slope(temp):
        """Slope of the ideal pH electrode, in V/pH"""

        # Properties of this Universe
        gas_const = 8.3144
        faraday_const = 96485
        abs_zero_temp = -273.15
        ln_10 = 2.3026

        return gas_const * (temp - abs_zero_temp) * ln_10 / faraday_const

    @staticmethod
    def compute_slope(temp, ph1, v1, ph2, v2):
        """Relative slope of the pH electrode. Equals 1 for the ideal electrode."""
        return (v1 - v2) / (ph2 - ph1) / PHTheory.ideal_slope(temp)

    @staticmethod
    def compute_offset(temp, slope, ph, v):
        """Offset voltage"""
        return v + slope * PHTheory.ideal_slope(temp) * (ph - 7)

    @staticmethod
    def compute_ph(temp, offset, slope, v):
        return 7 + (offset - v) / (slope * PHTheory.ideal_slope(temp))


class PHCalibration:
    """
    Parse calibration data.
    """

    def __init__(self):
        # Two point calibration only
        assert len(settings.PH_CALIBRATION['points']) == 2

        point1 = settings.PH_CALIBRATION['points'][0]
        point2 = settings.PH_CALIBRATION['points'][1]
        temp = settings.PH_CALIBRATION['temperature']

        self.slope = PHTheory.compute_slope(
            temp,
            point1['ph'], point1['voltage'],
            point2['ph'], point2['voltage'])

        if abs(self.slope - 1) > 0.2:
            raise Exception('pH slope %.2f is out of range, consider replacing the electrode' % self.slope)

        self.offset = PHTheory.compute_offset(
            temp, self.slope,
            point1['ph'], point1['voltage'])

        if abs(self.offset - settings.PH_ADC_REF_V / 2) > settings.PH_ADC_REF_V * 0.1:
            raise Exception('pH offset %.3f is out of range' % self.offset)

        print('pH slope %.2f offset %.3f' % (self.slope, self.offset))

    def compute_ph(self, temp, v):
        return PHTheory.compute_ph(temp, self.offset, self.slope, v)


class ADCInterface:
    """
    MCP3221 interface.
    """

    adc_bits = 12

    def value_to_voltage(self, value):
        return float(value) * settings.PH_ADC_REF_V / (1 << self.adc_bits)

    def __init__(self):
        self.i2c = smbus.SMBus(settings.PH_ADC_I2C_BUSN)

    def get_value(self):
        reading = self.i2c.read_i2c_block_data(settings.PH_ADC_I2C_ADDR, 0x00, 2)
        return (reading[0] << 8) + reading[1]

    def get_voltage(self):
        value = self.get_value()
        return self.value_to_voltage(value)


class PHInterface:
    """
    Complete pH electrode interface with
    calibration and temperature compensation.
    """

    def __init__(self):
        self.adc = ADCInterface()
        self.calibration = PHCalibration()

    def get_ph(self, temp):
        v = self.adc.get_voltage()
        return self.calibration.compute_ph(temp, v)


def main():
    ph = PHInterface()
    print("%.2f" % ph.get_ph(25))


if __name__ == "__main__":
    main()
