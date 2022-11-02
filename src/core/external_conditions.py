#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to store and look up data on external conditions
(e.g. external air temperature)

Calculation of solar radiation on a surface of a given orientation and tilt is
based on BS EN ISO 52010-1:2017.
"""

# Standard library imports
import sys
from math import cos, sin, tan, pi, asin, acos, radians, degrees

class ExternalConditions:
    """ An object to store and look up data on external conditions """

    def __init__(self,
            simulation_time,
            air_temps,
            wind_speeds,
            diffuse_horizontal_radiation,
            direct_beam_radiation,
            solar_reflectivity_of_ground,
            latitude,
            longitude,
            timezone,
            start_day,
            end_day,
            time_series_step,
            january_first,
            daylight_savings,
            leap_day_included,
            direct_beam_conversion_needed,
            shading_segments,
            ):
        """ Construct an ExternalConditions object

        Arguments:
        simulation_time -- reference to SimulationTime object
        air_temps       -- list of external air temperatures, in deg C (one entry per hour)
        wind_speeds     -- list of wind speeds, in m/s (one entry per hour)
        diffuse_horizontal_radiation    -- list of diffuse horizontal radiation values, in W/m2 (one entry per hour)
        direct_beam_radiation           -- list of direct beam radiation values, in W/m2 (one entry per hour)
        solar_reflectivity_of_ground    -- list of ground reflectivity values, 0 to 1 (one entry per hour)
        latitude        -- latitude of weather station, angle from south, in degrees (single value)
        longitude       -- longitude of weather station, easterly +ve westerly -ve, in degrees (single value)
        timezone        -- timezone of weather station, -12 to 12 (single value)
        start_day       -- first day of the time series, day of the year, 0 to 365 (single value)
        end_day         -- last day of the time series, day of the year, 0 to 365 (single value)
        time_series_step -- timestep of the time series data, in hours
        january_first   -- day of the week for January 1st, monday to sunday, 1 to 7 (single value)
        daylight_savings    -- handling of daylight savings time, (single value)
                            e.g. applicable and taken into account, 
                            applicable but not taken into account, 
                            not applicable
        leap_day_included   -- whether climate data includes a leap day, true or false (single value)
        direct_beam_conversion_needed -- A flag to indicate whether direct beam radiation from climate data needs to be 
                                        converted from horizontal to normal incidence. If normal direct beam radiation 
                                        values are provided then no conversion is needed.
        shading_segments -- data splitting the ground plane into segments (8-36) and giving height
                            and distance to shading objects surrounding the building
        """     

        self.__simulation_time  = simulation_time
        self.__air_temps        = air_temps
        self.__wind_speeds      = wind_speeds
        self.__diffuse_horizontal_radiation = diffuse_horizontal_radiation
        self.__direct_beam_radiation = direct_beam_radiation
        self.__solar_reflectivity_of_ground = solar_reflectivity_of_ground
        self.__latitude = latitude
        self.__longitude = longitude
        self.__timezone = timezone
        self.__start_day = start_day
        self.__end_day = end_day
        self.__january_first = january_first
        self.__daylight_savings = daylight_savings
        self.__leap_day_included = leap_day_included
        self.__direct_beam_conversion_needed = direct_beam_conversion_needed
        self.__shading_segments = shading_segments
        self.__time_series_step = time_series_step

    def testoutput_setup(self,tilt,orientation):
        """ print output to a file for analysis """

        #call this function once at the start of the calculation to test outputs

        import time
        readable = time.ctime()
        with open("test_sunpath.txt", "a") as o:
            o.write("\n")
            o.write("\n")
            o.write("*****************")
            o.write("\n")
            o.write(readable)
            o.write("\n")
            o.write("latitude " + str(self.latitude()))
            o.write("\n")
            o.write("longitude " + str(self.longitude()))
            o.write("\n")
            o.write("day of year " + str(self.start_day()))
            o.write("\n")
            o.write("surface tilt " + str(tilt))
            o.write("\n")
            o.write("surface orientation " + str(orientation))
            o.write("\n")
            o.write("sim hour,solar time,s declination,s hour angle,s altitude,s azimuth,air mass,sun surface azimuth,direct irad,solar angle of incidence,ET irad,F1,F2,E,delta,a over b,diffuse irad,ground reflect irad,circumsolar,final diffuse,final direct")


    def testoutput(self,tilt,orientation):
        """ print output to a file for analysis """

        #call this function once during every timestep to test outputs

        #write headers
        with open("test_sunpath.txt", "a") as o:
            o.write("\n")
            o.write(str(self.__simulation_time.hour_of_day()))
            o.write(",")
            o.write(str(self.solar_time()))
            o.write(",")
            o.write(str(self.solar_declination()))
            o.write(",")
            o.write(str(self.solar_hour_angle()))
            o.write(",")
            o.write(str(self.solar_altitude()))
            o.write(",")
            o.write(str(self.solar_azimuth_angle()))
            o.write(",")
            o.write(str(self.air_mass()))
            o.write(",")
            o.write(str(self.sun_surface_azimuth(orientation)))
            o.write(",")
            o.write(str(self.direct_irradiance(tilt, orientation)))
            o.write(",")
            o.write(str(self.solar_angle_of_incidence(tilt, orientation)))
            o.write(",")
            o.write(str(self.extra_terrestrial_radiation()))
            o.write(",")
            o.write(str(self.F1()))
            o.write(",")
            o.write(str(self.F2()))
            o.write(",")
            o.write(str(self.dimensionless_clearness_parameter()))
            o.write(",")
            o.write(str(self.dimensionless_sky_brightness_parameter()))
            o.write(",")
            o.write(str(self.a_over_b(tilt, orientation)))
            o.write(",")
            o.write(str(self.diffuse_irradiance(tilt, orientation)))
            o.write(",")
            o.write(str(self.ground_reflection_irradiance(tilt)))
            o.write(",")
            o.write(str(self.circumsolar_irradiance(tilt, orientation)))
            o.write(",")
            o.write(str(self.calculated_diffuse_irradiance(tilt, orientation)))
            o.write(",")
            o.write(str(self.calculated_direct_irradiance(tilt, orientation)))

    def air_temp(self):
        """ Return the external air temperature for the current timestep """
        return self.__air_temps[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def air_temp_annual(self):
        """ Return the average air temperature for the year """
        assert len(self.__air_temps) == 8760 # Only works if data for whole year has been provided
        return sum(self.__air_temps) / len(self.__air_temps)

    def air_temp_monthly(self):
        """ Return the average air temperature for the current month """
        # Get start and end hours for current month
        idx_start, idx_end = self.__simulation_time.current_month_start_end_hour()
        # Get air temperatures for the current month
        air_temps_month = self.__air_temps[idx_start:idx_end]

        return sum(air_temps_month) / len(air_temps_month)

    def ground_temp(self):
        """ Return the external ground temperature for the current timestep """
        return self.__ground_temps[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def wind_speed(self):
        """ Return the wind speed for the current timestep """
        return self.__wind_speeds[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def diffuse_horizontal_radiation(self):
        """ Return the diffuse_horizontal_radiation for the current timestep """
        return self.__diffuse_horizontal_radiation[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def direct_beam_radiation(self):
        """ Return the direct_beam_radiation for the current timestep """
        raw_value = self.__direct_beam_radiation[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]
        # if the climate data to only provide direct horizontal (rather than normal:
        # If only direct (beam) solar irradiance at horizontal plane is available in the climatic data set,
        # it shall be converted to normal incidence by dividing the value by the sine of the solar altitude.
        # for now I assume the direct beam in the inputs is normal incidence.
        if self.__direct_beam_conversion_needed:
            sin_asol = sin(radians(self.solar_altitude()))
            #prevent division by zero error. if sin_asol = 0 then the sun is lower than the
            #horizon and there will be no direct radiation to convert
            if sin_asol > 0:
                Gsol_b = raw_value / sin_asol
            else:
                Gsol_b = raw_value
        else:
            Gsol_b = raw_value

        return Gsol_b

    def solar_reflectivity_of_ground(self):
        """ Return the solar_reflectivity_of_ground for the current timestep """
        return self.__solar_reflectivity_of_ground[self.__simulation_time.time_series_idx(self.__start_day, self.__time_series_step)]

    def latitude(self):
        """ Return the latitude """
        return self.__latitude

    def longitude(self):
        """ Return the longitude """
        return self.__longitude

    def timezone(self):
        """ Return the timezone """
        return self.__timezone

    def start_day(self):
        """ Return the start_day """
        return self.__start_day
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently used as the current day value

    def end_day(self):
        """ Return the end_day """
        return self.__end_day
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # not current used

    def january_first(self):
        """ Return the january_first """
        return self.__january_first
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # not current used

    def daylight_savings(self):
        """ Return the daylight_savings """
        return self.__daylight_savings
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file
        # not current used

    def leap_day_included(self):
        """ Return the leap_day_included """
        return self.__leap_day_included
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file
        # not current used

    def earth_orbit_deviation(self):
        """ Calculate Rdc, the earth orbit deviation, as a function of the day, in degrees """

        nday = self.__simulation_time.current_day() + 1
        # nday is the day of the year, from 1 to 365 or 366 (leap year)
        # Note that current_day function returns days numbered 0 to 364 or 365,
        # so we need to add 1 above

        Rdc = (360 / 365) * nday

        return Rdc

    def solar_declination(self):
        """ Calculate solar declination in degrees """

        Rdc = radians(self.earth_orbit_deviation())
        # note we convert to radians for the python cos & sin inputs in formula below

        solar_declination = 0.33281 - 22.984 * cos(Rdc) - 0.3499 * cos(2 * Rdc) \
                          - 0.1398 * cos(3 * Rdc) + 3.7872 * sin(Rdc) + 0.03205 \
                          * sin(2 * Rdc) + 0.07187 * sin(3 * Rdc)

        return solar_declination

    def equation_of_time(self):
        """ Calculate the equation of time """

        """ 
        teq is the equation of time, in minutes;
        nday is the day of the year, from 1 to 365 or 366 (leap year)
        """    

        nday = self.__simulation_time.current_day() + 1
        # nday is the day of the year, from 1 to 365 or 366 (leap year)
        # Note that current_day function returns days numbered 0 to 364 or 365,
        # so we need to add 1 here

        # note we convert the values inside the cos() to radians for the python function
        # even though the 180 / pi is converting from radians into degrees
        # this way the formula remains consistent with as written in the ISO document

        if   nday < 21:
            teq = 2.6 + 0.44 * nday
        elif nday < 136:
            teq = 5.2 + 9.0 * cos((nday - 43) * 0.0357)
        elif nday < 241:
            teq = 1.4 - 5.0 * cos((nday - 135) * 0.0449)
        elif nday < 336:
            teq = -6.3 - 10.0 * cos((nday - 306) * 0.036)
        elif nday <= 366:
            teq = 0.45 * (nday - 359)
        else:
            sys.exit("Day of the year ("+str(nday)+") not valid")

        return teq

    def time_shift(self):
        """ Calculate the time shift, in hours, resulting from the fact that the 
        longitude and the path of the sun are not equal

        NOTE Daylight saving time is disregarded in tshift which is time independent
        """

        tshift = self.timezone() - self.longitude() / 15
        return tshift

    def solar_time(self):
        """ Calculate the solar time, tsol, as a function of the equation of time, 
        the time shift and the hour of the day """

        """ 
        tsol is the solar time, in h
        nhour is the actual (clock) time for the location, the hour of the day, in h
        """
        nhour = self.__simulation_time.hour_of_day() + 1
        #note we +1 here because the simulation hour of day starts at 0
        #while the sun path standard hour of day starts at 1 (hour 0 to 1)
        tsol = nhour - (self.equation_of_time() / 60) - self.time_shift()

        return tsol

    def solar_hour_angle(self):
        """ Calculate the solar hour angle, in the middle of the 
        current hour as a function of the solar time """

        # TODO How is this to be adjusted for timesteps that are not hourly?
        # would allowing solar_time to be a decimal be all that is needed?

        """ 
        w is the solar hour angle, in degrees

        Notes from ISO 52020 6.4.1.5
        NOTE 1 The limitation of angles ranging between -180 and +180 degrees is 
        needed to determine which shading objects are in the direction of the sun; 
        see also the calculation of the azimuth angle of the sun in 6.4.1.7.
        NOTE 2 Explanation of "12.5": The hour numbers are actually hour sections: 
        the first hour section of a day runs from 0h to 1h. So, the average position 
        of the sun for the solar radiation measured during (solar) hour section N is 
        at (solar) time = (N -0,5) h of the (solar) day.
        """

        w = (180 / 12) * (12.5 - self.solar_time())

        if w > 180:
            w = w - 360
        elif w < -180:
            w = w + 360

        return w

    def solar_altitude(self):
        """  the angle between the solar beam and the horizontal surface, determined 
             in the middle of the current hour as a function of the solar hour angle, 
             the solar declination and the latitude """

        # TODO How is this to be adjusted for timesteps that are not hourly?
        # would allowing solar_time to be a decimal be all that is needed?

        """ 
        asol is the solar altitude angle, the angle between the solar beam 
        and the horizontal surface, in degrees;
        """

        # note that we convert to radians for the sin & cos python functions and then
        # we need to convert the result back to degrees after the arcsin transformation

        asol = asin( sin(radians(self.solar_declination())) * sin(radians(self.latitude())) \
                    + cos(radians(self.solar_declination())) * cos(radians(self.latitude())) * cos(radians(self.solar_hour_angle())))

        if degrees(asol) < 0.0001:
            return (0)

        return degrees(asol)

    def solar_zenith_angle(self):
        """  the complementary angle of the solar altitude """

        zenith = 90 - self.solar_altitude()

        return zenith

    def solar_azimuth_angle(self):
        """  calculates the solar azimuth angle,
        angle from South, eastwards positive, westwards negative, in degrees """

        """
        NOTE The azimuth angles range between −180 and +180 degrees; this is needed to determine which shading 
        objects are in the direction of the sun
        """

        sin_aux1_numerator = cos(radians(self.solar_declination())) * sin(radians(180 - self.solar_hour_angle()))

        cos_aux1_numerator = cos(radians(self.latitude())) \
                    * sin(radians(self.solar_declination())) + sin(radians(self.latitude())) \
                    * cos(radians(self.solar_declination())) \
                    * cos(radians(180 - self.solar_hour_angle()))

        denominator = cos(asin(sin(radians(self.solar_altitude()))))

        sin_aux1 = sin_aux1_numerator / denominator            
        cos_aux1 = cos_aux1_numerator / denominator 
        aux2 = degrees(asin(sin_aux1_numerator) / denominator)

        # BS EN ISO 52010-1:2017. Formula 16
        if (sin_aux1 >= 0 and cos_aux1 > 0):
            solar_azimuth = 180 - aux2
            if solar_azimuth < 0:
                solar_azimuth = -solar_azimuth
        elif cos_aux1 < 0:
            solar_azimuth = aux2
        else:
            solar_azimuth = -(180 + aux2)

        return solar_azimuth

    def air_mass(self):
        """  calculates the air mass, m, the distance the solar beam travels through the earth atmosphere.
        The air mass is determined as a function of the sine of the solar altitude angle """

        sa = self.solar_altitude()

        if sa >= 10:
            m = 1 / sin(radians(sa))
        else:
            m = 1 / (sin(radians(sa)) + 0.15 * (sa + 3.885)**-1.253)

        return m

    def solar_angle_of_incidence(self, tilt, orientation):
        """  calculates the solar angle of incidence, which is the angle of incidence of the 
        solar beam on an inclined surface and is determined as function of the solar hour angle 
        and solar declination 
        
        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        # set up the parameters first just to make the very long equation slightly more readable     
        sin_dec = sin(radians(self.solar_declination()))
        cos_dec = cos(radians(self.solar_declination()))
        sin_lat = sin(radians(self.latitude()))
        cos_lat = cos(radians(self.latitude()))
        sin_t = sin(radians(tilt))
        cos_t = cos(radians(tilt))
        sin_o = sin(radians(orientation))
        cos_o = cos(radians(orientation))
        sin_sha = sin(radians(self.solar_hour_angle()))
        cos_sha = cos(radians(self.solar_hour_angle()))

        solar_angle_of_incidence = acos( \
                                   sin_dec * sin_lat * cos_t \
                                 - sin_dec * cos_lat * sin_t * cos_o \
                                 + cos_dec * cos_lat * cos_t * cos_sha \
                                 + cos_dec * sin_lat * sin_t * cos_o * cos_sha \
                                 + cos_dec * sin_t * sin_o * sin_sha \
                                 )

        return degrees(solar_angle_of_incidence)

    def sun_surface_azimuth(self, orientation):
        """  calculates the azimuth angle between sun and the inclined surface,
        needed as input for the calculation of the irradiance in case of solar shading by objects 

        Arguments:

        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;

        """

        test_angle = self.solar_hour_angle() - orientation

        if test_angle > 180:
            azimuth = -360 + test_angle
        elif test_angle < -180:
            azimuth = 360 + test_angle
        else:
            azimuth = test_angle

        return azimuth

    def sun_surface_tilt(self, tilt):
        """  calculates the tilt angle between sun and the inclined surface,
        needed as input for the calculation of the irradiance in case of solar shading by objects 

        Arguments:

        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;

        """

        test_angle = tilt - self.solar_zenith_angle()

        if test_angle > 180:
            sun_surface_tilt = -360 + test_angle
        elif test_angle < -180:
            sun_surface_tilt = 360 + test_angle
        else:
            sun_surface_tilt = test_angle

        return sun_surface_tilt

    # TODO section 6.4.2 of ISO 52010 is not implemented here as it relates to methods of
    # obtaiing the needed irradiance values if they are not available from the climatic dataset.
    # If we decide this might be useful later then my suggestion would be to implement this as a
    # preprocessing step so that the core calculation always recieves the 'correct' climate data.

    # TODO solar reflectivity of the ground is expected to be initially fixed at 0.2, as per the 
    # default listed in ISO 52010 Annex B. However, the implementation here allows for one value 
    # per time step so alternative methods can be used in the future. options include taking values
    # from a climatic dataset that contains them, basing the values on ground surface material,
    # or ground cover such as snow. This can be implemented in a preprocess rather than the core.

    def direct_irradiance(self, tilt, orientation):
        """  calculates the direct irradiance on the inclined surface, determined as function 
        of cosine of the solar angle of incidence and the direct normal (beam) solar irradiance
        NOTE The solar beam irradiance is defined as falling on an surface normal to the solar beam. 
        This is not the same as direct horizontal radiation.

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
                          
        """

        direct_irradiance = max(0, self.direct_beam_radiation() * cos(radians(self.solar_angle_of_incidence(tilt, orientation))))

        return direct_irradiance

    def extra_terrestrial_radiation(self):
        """  calculates the extra terrestrial radiation, the normal irradiance out of the atmosphere 
        as a function of the day

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
                          
        """

        #NOTE the ISO 52010 has an error in this formula.
        #it lists Gsol,c as the solar angle of incidence on the inclined surface
        #when it should be the solar constant, given elsewhere as 1367
        #we use the correct version of the formula here

        extra_terrestrial_radiation = 1367 * (1 + 0.033 * cos(radians(self.earth_orbit_deviation())))

        return extra_terrestrial_radiation

    def brightness_coefficient(self, E, Fij):
        """ returns brightness coefficient as a look up from Table 8 in ISO 52010 

        Arguments:
        E    -- dimensionless clearness parameter
        Fij  -- the coefficient to be returned. e.g. f12 or f23
        """

        #TODO I've not had a need for the clearness index parameters contained in this table yet, 
        #if they are needed as input or output later then this function can be reworked

        if E < 1.065:
            # overcast
            index = 1
        elif E < 1.23:
            index = 2
        elif E < 1.5:
            index = 3
        elif E < 1.95:
            index = 4
        elif E < 2.8:
            index = 5
        elif E < 4.5:
            index = 6
        elif E < 6.2:
            index = 7
        else:
            #clear
            index = 8

        brightness_coeff_dict = {
            1: {'f11': -0.008, 'f12': 0.588, 'f13': -0.062, 'f21': -0.06, 'f22': 0.072, 'f23': -0.022},
            2: {'f11': 0.13, 'f12': 0.683, 'f13': -0.151, 'f21': -0.019, 'f22': 0.066, 'f23': -0.029},
            3: {'f11': 0.33, 'f12': 0.487, 'f13': -0.221, 'f21': 0.055, 'f22': -0.064, 'f23': -0.026},
            4: {'f11': 0.568, 'f12': 0.187, 'f13': -0.295, 'f21': 0.109, 'f22': -0.152, 'f23': -0.014},
            5: {'f11': 0.873, 'f12': -0.392, 'f13': -0.362, 'f21': 0.226, 'f22': -0.462, 'f23': 0.001},
            6: {'f11': 1.132, 'f12': -1.237, 'f13': -0.412, 'f21': 0.288, 'f22': -0.823, 'f23': 0.056},
            7: {'f11': 1.06, 'f12': -1.6, 'f13': -0.359, 'f21': 0.264, 'f22': -1.127, 'f23': 0.131},
            8: {'f11': 0.678, 'f12': -0.327, 'f13': -0.25, 'f21': 0.156, 'f22': -1.377, 'f23': 0.251}
            }

        return brightness_coeff_dict[index][Fij]

    def F1(self):
        """ returns the circumsolar brightness coefficient, F1

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        E = self.dimensionless_clearness_parameter()
        delta = self.dimensionless_sky_brightness_parameter()

        #brightness coeffs
        f11 = self.brightness_coefficient(E, 'f11')
        f12 = self.brightness_coefficient(E, 'f12')
        f13 = self.brightness_coefficient(E, 'f13')
        #The formulation of F1 is made so as to avoid non-physical negative values 
        #that may occur and result in unacceptable distortions if the model is used 
        #for very low solar elevation angles
        F1 = max(0, f11 + f12 * delta + f13 * (pi * self.solar_zenith_angle() / 180))

        return F1

    def F2(self):
        """ returns the horizontal brightness coefficient, F2

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        E = self.dimensionless_clearness_parameter()
        delta = self.dimensionless_sky_brightness_parameter()

        #horizontal brightness coefficient, F2
        f21 = self.brightness_coefficient(E, 'f21')
        f22 = self.brightness_coefficient(E, 'f22')
        f23 = self.brightness_coefficient(E, 'f23')
        #F2 does not have the same restriction of max 0 as F1
        #from the EnergyPlus Engineering Reference:
        #The horizon brightening is assumed to be a linear source at the horizon 
        #and to be independent of azimuth. In actuality, for clear skies, the 
        #horizon brightening is highest at the horizon and decreases in intensity 
        #away from the horizon. For overcast skies the horizon brightening has a 
        #negative value since for such skies the sky radiance increases rather than 
        #decreases away from the horizon.
        F2 = f21 + f22 * delta + f23 * (pi * self.solar_zenith_angle() / 180)

        return F2

    def dimensionless_clearness_parameter(self):
        """ returns the dimensionless clearness parameter, E, anisotropic sky conditions (Perez model)"""

        Gsol_d = self.diffuse_horizontal_radiation()
        Gsol_b = self.direct_beam_radiation()
        asol = self.solar_altitude()

        #constant parameter for the clearness formula, K, in rad^-3 from table 9 of ISO 52010
        K = 1.014

        if Gsol_d == 0:
            E = 999
        else:
            E = (((Gsol_d + Gsol_b) / Gsol_d) + K * (pi / 180 * asol)**3) \
              / (1 + K * (pi / 180 * asol)**3)

        return E

    def dimensionless_sky_brightness_parameter(self):
        """  calculates the dimensionless sky brightness parameter, delta

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;

        """

        delta = self.air_mass() * self.diffuse_horizontal_radiation() \
              / self.extra_terrestrial_radiation()

        return delta

    def a_over_b(self, tilt, orientation):
        """  calculates the ratio of the parameters a and b

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        #dimensionless parameters a & b
        #describing the incidence-weighted solid angle sustained by the circumsolar region as seen 
        #respectively by the tilted surface and the horizontal. 
        a = max(0, cos(radians(self.solar_angle_of_incidence(tilt, orientation))))
        b = max(cos(radians(85)), cos(radians(self.solar_zenith_angle())))

        return a / b


    def diffuse_irradiance(self, tilt, orientation):
        """  calculates the diffuse part of the irradiance on the surface (without ground reflection)

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        #first set up parameters needed for the calculation
        Gsol_d = self.diffuse_horizontal_radiation()
        F1 = self.F1()
        F2 = self.F2()
        a_over_b = self.a_over_b(tilt, orientation)

        #main calculation using all the above parameters
        diffuse_irradiance = Gsol_d * ( (1 - F1) \
                            * ((1 + cos(radians(tilt))) / 2) \
                            + F1 * a_over_b + F2 * sin(radians(tilt)) \
                            )

        return diffuse_irradiance

    def ground_reflection_irradiance(self, tilt):
        """  calculates the contribution of the ground reflection to the irradiance on the inclined surface, 
        determined as function of global horizontal irradiance, which in this case is calculated from the solar 
        altitude, diffuse and beam solar irradiance and the solar reflectivity of the ground

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        """

        #first set up parameters needed for the calculation
        Gsol_d = self.diffuse_horizontal_radiation()
        Gsol_b = self.direct_beam_radiation()
        asol = radians(self.solar_altitude())

        ground_reflection_irradiance = (Gsol_d + Gsol_b * sin(asol)) * self.solar_reflectivity_of_ground() \
                                     * ((1 - cos(radians(tilt))) / 2)

        return ground_reflection_irradiance

    def circumsolar_irradiance(self, tilt, orientation):
        """  calculates the circumsolar_irradiance

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        Gsol_d = self.diffuse_horizontal_radiation()
        F1 = self.F1()
        a_over_b = self.a_over_b(tilt, orientation)

        circumsolar_irradiance = Gsol_d * F1 * a_over_b

        return circumsolar_irradiance

    def calculated_direct_irradiance(self, tilt, orientation):
        """  calculates the total direct irradiance on an inclined surface including circumsolar

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        calculated_direct = self.direct_irradiance(tilt, orientation) + self.circumsolar_irradiance(tilt, orientation)

        return calculated_direct

    def calculated_diffuse_irradiance(self, tilt, orientation):
        """  calculates the total diffuse irradiance on an inclined surface excluding circumsolar
        and including ground reflected irradiance

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
        """

        calculated_diffuse = self.diffuse_irradiance(tilt, orientation) \
                           - self.circumsolar_irradiance(tilt, orientation) \
                           + self.ground_reflection_irradiance(tilt)

        return calculated_diffuse

    def calculated_total_solar_irradiance(self, tilt, orientation):
        """  calculates the hemispherical or total solar irradiance on the inclined surface 
        without the effect of shading

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
                          
        """

        total_irradiance = self.calculated_direct_irradiance(tilt, orientation) \
                         + self.calculated_diffuse_irradiance(tilt, orientation)

        return total_irradiance

    # end of sun path calculations from ISO 52010
    # below are overshading calculations from ISO 52016

    def outside_solar_beam(self, tilt, orientation):
        """ checks if the shaded surface is in the view of the solar beam.
        if not, then shading is complete, total direct rad = 0 and no further
        shading calculation needed for this object for this time step. returns
        a flag for whether the surface is outside solar beam

        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the 
                          inclined surface normal, -180 to 180, in degrees;
                          
        """

        test1 = orientation - self.solar_azimuth_angle()
        test2 = tilt - self.solar_altitude()

        if (-90 > test1 or test1 > 90):
            # surface outside solar beam
            return 1
        elif (-90 > test2 or test2 > 90):
            # surface outside solar beam
            return 1
        else:
            # surface inside solar beam
            return 0

    def get_segment(self):
        """ for complex (environment) shading objects, we need to know which
        segment the azimuth of the sun occupies at each timestep

        """

        azimuth = self.solar_azimuth_angle()

        for segment in self.__shading_segments:
            if (azimuth < segment["start"] and azimuth > segment["end"]):
                return segment
        #if not exited function yet then segment has not been found and there
        #is some sort of error
        sys.exit("solar segment not found. Check shading inputs")

    def obstacle_shading_height(self, Hkbase, Hobst, Lkobst ):
        """ calculates the height of the shading on the shaded surface (k),
        from the shading obstacle in segment i at time t. Note that "obstacle"
        has a specific meaning in ISO 52016 Annex F

        Arguments:
        Hkbase        -- is the base height of the shaded surface k, in m
        Hobst         -- is the height of the shading obstacle, p, in segment i, in m
        Lkobst        -- is the horizontal distance between the shaded surface k, in m 
                         and the shading obstacle p in segment i, in m
        """

        Hshade = max(0, Hobst - Hkbase - Lkobst * tan(self.solar_altitude()))
        return Hshade

    def overhang_shading_height(self, Hk, Hkbase, Hovh, Lkovh ):
        """ calculates the height of the shading on the shaded surface (k),
        from the shading overhang in segment i at time t. Note that "overhang"
        has a specific meaning in ISO 52016 Annex F

        Arguments:
        Hk            -- is the height of the shaded surface, k, in m
        Hkbase        -- is the base height of the shaded surface k, in m
        Hovh          -- is the lowest height of the overhang q, in segment i, in m
        Lkovh         -- is the horizontal distance between the shaded surface k 
                         and the shading overhang, q, in segment i, in m
        """

        Hshade = max(0, Hk + Hkbase - Hovh + Lkovh * tan(self.solar_altitude()))
        return Hshade

    def direct_shading_reduction_factor(self, base_height, height, width, orientation, window_shading):
        """ calculates the shading factor of direct radiation due to external
        shading objects

        Arguments:
        height         -- is the height of the shaded surface (if surface is tilted then
                          this must be the vertical projection of the height), in m
        base_height    -- is the base height of the shaded surface k, in m
        width          -- is the width of the shaded surface, in m
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the 
                          inclined surface normal, -180 to 180, in degrees;
        window_shading -- data on overhangs and side fins associated to this building element
                          includes the shading object type, depth, anf distance from element
        """

        # start with default assumption of no shading
        Hshade_obst = 0
        Hshade_ovh = 0
        WfinR = 0
        WfinL = 0

        #first process the distant (environment) shading for this building element

        #get the shading segment we are currently in
        segment = self.get_segment()
        #check for any shading objects in this segment
        if "shading" in segment.keys():
            for shade_obj in segment["shading"]:
                if shade_obj["type"] == "obstacle":
                    new_shade_height = self.obstacle_shading_height \
                    (base_height, shade_obj["height"], shade_obj["distance"])

                    Hshade_obst = max(Hshade_obst, new_shade_height)
                elif shade_obj["type"] == "overhang":
                    new_shade_height = self.overhang_shading_height \
                    (height, base_height, shade_obj["height"], shade_obj["distance"])

                    Hshade_ovh = max(Hshade_ovh, new_shade_height)
                else:
                    sys.exit("shading object type" + shade_obj["type"] + "not recognised")

        # then check if there is any simple shading on this building element
        # (note only applicable to transparent building elements so window_shading
        # will always be False for other elements)
        if window_shading:
            altitude = self.solar_altitude()
            azimuth = self.solar_azimuth_angle()
            # if there is then loop through all objects and calc shading heights/widths
            for shade_obj in window_shading:
                depth = shade_obj["depth"]
                distance = shade_obj["distance"]
                if shade_obj["type"] == "overhang":
                    new_shade_height = (depth * tan(radians(altitude)) \
                                    / cos(radians(azimuth - orientation))) \
                                    - distance

                    Hshade_ovh = max(Hshade_ovh, new_shade_height)
                elif shade_obj["type"] == "sidefinright":
                    #check if the sun is in the opposite direction
                    check = azimuth - orientation
                    if check > 0:
                        new_finRshade = 0
                    else:
                        new_finRshade = depth * tan(radians(azimuth - orientation)) \
                                        - distance
                    WfinR = max(WfinR, new_finRshade)
                elif shade_obj["type"] == "sidefinleft":
                    #check if the sun is in the opposite direction
                    check = azimuth - orientation
                    if check < 0:
                        new_finLshade = 0
                    else:
                        new_finLshade = depth * tan(radians(azimuth - orientation)) \
                                        - distance
                    WfinL = max(WfinL, new_finLshade)
                else:
                    sys.exit("shading object type" + shade_obj["type"] + "not recognised")

        # The height of the shade on the shaded surface from all obstacles is the 
        # largest of all, with as maximum value the height of the shaded object
        Hk_obst = min(height, Hshade_obst)

        # The height of the shade on the shaded surface from all overhangs is the 
        # largest of all, with as maximum value the height of the shaded object
        Hk_ovh = min(height, Hshade_ovh)

        # The height of the remaining sunlit area on the shaded surface from 
        # all obstacles and all overhangs
        Hk_sun = max(0, height - (Hk_obst + Hk_ovh))

        # The width of the shade on the shaded surface from all right side fins 
        # is the largest of all, with as maximum value the width of the shaded object
        Wk_finR = min(width, WfinR)

        # The width of the shade on the shaded surface from all left side fins 
        # is the largest of all, with as maximum value the width of the shaded object
        Wk_finL = min(width, WfinL)

        # The width of the remaining sunlit area on the shaded surface from all 
        # right hand side fins and all left hand side fins
        Wk_sun = max(0, width - (Wk_finR + Wk_finL))

        # And then the direct shading reduction factor of the shaded surface for 
        # obstacles, overhangs and side fins
        Fdir = (Hk_sun * Wk_sun) / (height * width)

        return Fdir

    def shading_reduction_factor(self, base_height, height, width, tilt, orientation, window_shading):
        """ calculates the shading factor due to external
        shading objects

        Arguments:
        height         -- is the height of the shaded surface (if surface is tilted then
                          this must be the vertical projection of the height), in m
        base_height    -- is the base height of the shaded surface k, in m
        width          -- is the width of the shaded surface, in m
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the 
                          inclined surface normal, -180 to 180, in degrees;
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        window_shading -- data on overhangs and side fins associated to this building element
                          includes the shading object type, depth, anf distance from element
        """

        # first chceck if there is any radiation. This is needed to prevent a potential 
        # divide by zero error in the final step, but also, if there is no radiation 
        # then shading is irrelevant and we can skip the whole calculation
        direct = self.calculated_direct_irradiance(tilt, orientation)
        diffuse = self.calculated_diffuse_irradiance(tilt, orientation)
        if direct + diffuse == 0:
            return 0

        # first check if the surface is outside the solar beam
        # if so then direct shading is complete and we don't need to
        # calculate shading from objects
        if self.outside_solar_beam(tilt, orientation):
            Fdir = 0
        else:
            Fdir = self.direct_shading_reduction_factor \
                    (base_height, height, width, orientation, window_shading)

        return Fdir

        # TODO suspected bug identified in ISO 52016 as it conflicts with ISO 52010:
        #ISO 52010 states that (6.4.5.2.1) the total irradiance on the inclined surface is
        #Itotal = Fdir * Idirect + Idiffuse
        #This is how the shading factor is used with the solar gains calculation.
        #However, ISO 52016 takes Fdir and performs the calculation below to give a "final"
        #shading factor. This does not make sense to be applied solely to the direct radiation
        #when calculating solar gains. Therefore we return Fdir here.

        #Fshade = (Fdir * direct + diffuse) / (direct + diffuse)

        #return Fshade
