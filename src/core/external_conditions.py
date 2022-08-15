#!/usr/bin/env python3

""" TODO Copyright & licensing notices

This module provides object(s) to store and look up data on external conditions
(e.g. external air temperature)
"""

# Standard library imports
import sys
from math import cos, sin, pi, asin, acos, radians, degrees

class ExternalConditions:
    """ An object to store and look up data on external conditions """

    def __init__(self, 
            simulation_time, 
            air_temps, 
            ground_temps, 
            diffuse_horizontal_radiation,
            direct_beam_radiation,
            solar_reflectivity_of_ground,
            latitude,
            longitude,
            timezone,
            start_day,
            end_day,
            january_first,
            daylight_savings,
            leap_day_included
            ):
        """ Construct an ExternalConditions object

        Arguments:
        simulation_time -- reference to SimulationTime object
        air_temps       -- list of external air temperatures, in deg C (one entry per timestep)
        ground_temps    -- list of external ground temperatures, in deg C (one entry per timestep)
        diffuse_horizontal_radiation    -- list of diffuse horizontal radiation values, in W/m2 (one entry per timestep)
        direct_beam_radiation           -- list of direct beam radiation values, in W/m2 (one entry per timestep)
        solar_reflectivity_of_ground    -- list of ground reflectivity values, 0 to 1 (one entry per timestep)
        latitude        -- latitude of weather station, angle from south, in degrees (single value)
        longitude       -- longitude of weather station, easterly +ve westerly -ve, in degrees (single value)
        timezone        -- timezone of weather station, -12 to 12 (single value)
        start_day       -- first day of the time series, day of the year, 1 to 366 (single value)
        end_day         -- last day of the time series, day of the year, 1 to 366 (single value)
        january_first   -- day of the week for January 1st, monday to sunday, 1 to 7 (single value)
        daylight_savings    -- handling of daylight savings time, (single value)
                            e.g. applicable and taken into account, 
                            applicable but not taken into account, 
                            not applicable
        leap_day_included   -- whether climate data includes a leap day, true or false (single value)
        """
        self.__simulation_time  = simulation_time
        self.__air_temps        = air_temps
        self.__ground_temps     = ground_temps
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

    def air_temp(self):
        """ Return the external air temperature for the current timestep """
        return self.__air_temps[self.__simulation_time.current_hour()]
        # TODO Assumes air temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def ground_temp(self):
        """ Return the external ground temperature for the current timestep """
        return self.__ground_temps[self.__simulation_time.current_hour()]
        # TODO Assumes ground temps list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
        
    def diffuse_horizontal_radiation(self):
        """ Return the diffuse_horizontal_radiation for the current timestep """
        return self.__diffuse_horizontal_radiation[self.__simulation_time.index()]
        # TODO Assumes diffuse_horizontal_radiation list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.
        
    def direct_beam_radiation(self):
        """ Return the direct_beam_radiation for the current timestep """
        return self.__direct_beam_radiation[self.__simulation_time.index()]
        # TODO Assumes direct_beam_radiation list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

    def solar_reflectivity_of_ground(self):
        """ Return the solar_reflectivity_of_ground for the current timestep """
        return self.__solar_reflectivity_of_ground[self.__simulation_time.index()]
        # TODO Assumes solar_reflectivity_of_ground list is one entry per timestep but in
        #      future it could be e.g. hourly figures even if timestep is
        #      sub-hourly. This would require the SimulationTime class to
        #      support such lookups.

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
    
    def end_day(self):
        """ Return the end_day """
        return self.__end_day
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
    
    def january_first(self):
        """ Return the january_first """
        return self.__january_first
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided

    def daylight_savings(self):
        """ Return the daylight_savings """
        return self.__daylight_savings
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file

    def leap_day_included(self):
        """ Return the leap_day_included """
        return self.__leap_day_included
        # TODO possibly this input sits better within simulation_time
        # but included here until final form decided
        # currently unclear whether this is reffering to a choice by the user
        # or a statement of the contents of the weather data file
        
    def earth_orbit_deviation(self):
        """ Calculate Rdc, the earth orbit deviation, as a function of the day, in degrees """
        
        nday = self.start_day()
        #TODO nday is the day of the year, from 1 to 365 or 366 (leap year)
        #I assume eventually nday will be returnable from a function in
        #simulation_time but for now we just use the start day
        
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
        
        nday = self.start_day()
        #TODO I assume eventually nday will be returnable from a function in
        #simulation_time but for now we just use the start day
        
        # note we convert the values inside the cos() to radians for the python function
        # even though the 180 / pi is converting from radians into degrees
        # this way the formula remains consistent with as written in the ISO document
        
        if   nday < 21:
            teq = 2.6 + 0.44 * nday
        elif nday < 136:
            teq = 5.2 + 9.0 * cos(radians((nday - 43) * 0.0357 * (180 / pi)))
        elif nday < 241:
            teq = 1.4 - 5.0 * cos(radians((nday - 135) * 0.0449 * (180 / pi)))
        elif nday < 336:
            teq = -6.3 - 10.0 * cos(radians((nday - 306) * 0.036 * (180 / pi)))
        elif nday <= 366:
            teq = 0.45 * (nday - 359)
        else:
            sys.exit("Day of the year ("+str(nday)+") not valid")
            
        return teq
        
    def time_shift(self):
        """ Calculate the time shift resulting from the fact that the 
        longitude and the path of the sun are not equal """
        
        """ 
        tshift is the time shift, in h
        TZ is the time zone, the actual (clock) time for the location compared to UTC, in h;
        λw is the longitude of the weather station, in degrees
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
        
        nhour = self.__simulation_time.current()
        #TODO nhour is the actual clock hour of the day. But we currently can't
        #calculate that from the inputs since the timestep is defined as being from an
        #arbitrary zero point. suggestion would be to allow input of the start day 
        #for the calculation and always begin at midnight.
        #using 'current' simulation time for now as a proxy.

        tsol = nhour - (self.equation_of_time() / 60) - self.time_shift()
        
        return tsol    
        
    def solar_hour_angle(self):
        """ Calculate the solar hour angle, ω, in the middle of the 
        current hour as a function of the solar time """
        
        # TODO How is this to be adjusted for timesteps that are not hourly?
        # would allowing solar_time to be a decimal be all that is needed?
        
        """ 
        w is the solar hour angle, in degrees
        
        Notes from ISO 52020 6.4.1.5
        NOTE 1 The limitation of angles ranging between −180 and +180 degrees is 
        needed to determine which shading objects are in the direction of the sun; 
        see also the calculation of the azimuth angle of the sun in 6.4.1.7.
        NOTE 2 Explanation of “12.5”: The hour numbers are actually hour sections: 
        the first hour section of a day runs from 0h to 1h. So, the average position 
        of the sun for the solar radiation measured during (solar) hour section N is 
        at (solar) time = (N –0,5) h of the (solar) day.
        
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
        
        if (sin_aux1 >= 0 and cos_aux1 > 0):
            solar_azimuth = 180 - aux2
        elif cos_aux1 < 0:
            solar_azimuth = aux2
        else:
            solar_azimuth = -180 + aux2
            
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
        
    # TODO from here onwards we are calculating the interaction between the solar beam and
    # the surface, taking into account orientation and pitch. If this file is to be split then 
    # this would be the optimum place to do it.
    
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
    
    # TODO one exception to the above could be this if we expect the climate data to only provide
    # direct horizontal (rather than normal?:
    # If only direct (beam) solar irradiance at horizontal plane is available in the climatic data set,
    # it shall be converted to normal incidence by dividing the value by the sine of the solar altitude.
    # for now I assume the direct beam in the inputs is normal incidence.
    
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
        
        direct_irradiance = max(0, self.direct_beam_radiation(), cos(radians(self.solar_angle_of_incidence(tilt, orientation))))
    
        return direct_irradiance
    
    def extra_terrestrial_radiation(self, tilt, orientation):
        """  calculates the extra terrestrial radiation, the normal irradiance out of the atmosphere 
        as a function of the day
        
        Arguments:
        tilt           -- is the tilt angle of the inclined surface from horizontal, measured 
                          upwards facing, 0 to 180, in degrees;
        orientation    -- is the orientation angle of the inclined surface, expressed as the 
                          geographical azimuth angle of the horizontal projection of the inclined 
                          surface normal, -180 to 180, in degrees;
                          
        """
        
        extra_terrestrial_radiation = self.solar_angle_of_incidence(tilt, orientation) \
                                    * (1 + 0.033 * cos(radians(self.earth_orbit_deviation())))
    
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
        Gsol_b = self.direct_beam_radiation()
        asol = self.solar_altitude()
        
        #dimensionless parameters a & b
        a = max(0, cos(radians(self.solar_angle_of_incidence(tilt, orientation))))
        b = max(cos(radians(85)), cos(radians(self.solar_zenith_angle())))
        
        #constant parameter for the clearness formula, K, in rad^-3 from table 9 of ISO 52010
        K = 1.014
        
        #dimensionless clearness parameter, anisotropic sky conditions (Perez model)
        if Gsol_d == 0:
            E = 999
        else:
            E = (((Gsol_d + Gsol_b) / Gsol_d) + K * (pi / 180 * asol)**3) \
              / (1 + K * (pi / 180 * asol)**3)
              
        #dimensionless sky brightness parameter
        delta = self.air_mass() * Gsol_d / self.extra_terrestrial_radiation(tilt, orientation)
        
        #circumsolar brightness coefficient, F1
        f11 = self.brightness_coefficient(E, 'f11')
        f12 = self.brightness_coefficient(E, 'f12')
        f13 = self.brightness_coefficient(E, 'f13')
        F1 = max(0, f11 + f12 * delta + f13 * (pi * self.solar_zenith_angle() / 180))
        
        #horizontal brightness coefficient, F2
        f21 = self.brightness_coefficient(E, 'f21')
        f22 = self.brightness_coefficient(E, 'f22')
        f23 = self.brightness_coefficient(E, 'f23')
        F2 = f21 + f22 * delta + f23 * (pi * self.solar_zenith_angle() / 180)
        
        #main calculation using all the above parameters
        diffuse_irradiance = Gsol_d * ( (1 - F1) \
                            * ((1 + cos(radians(tilt))) / 2) \
                            + F1 * (a / b) + F2 * sin(radians(tilt)) \
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
        #first set up parameters needed for the calculation
        Gsol_d = self.diffuse_horizontal_radiation()
        Gsol_b = self.direct_beam_radiation()
        asol = self.solar_altitude()
        
        #dimensionless parameters a & b
        a = max(0, cos(radians(self.solar_angle_of_incidence(tilt, orientation))))
        b = max(cos(radians(85)), cos(radians(self.solar_zenith_angle())))
        
        #constant parameter for the clearness formula, K, in rad^-3 from table 9 of ISO 52010
        K = 1.014
        
        #dimensionless clearness parameter, anisotropic sky conditions (Perez model)
        if Gsol_d == 0:
            E = 999
        else:
            E = (((Gsol_d + Gsol_b) / Gsol_d) + K * (pi / 180 * asol)**3) \
              / (1 + K * (pi / 180 * asol)**3)
              
        #dimensionless sky brightness parameter
        delta = self.air_mass() * Gsol_d / self.extra_terrestrial_radiation(tilt, orientation)
        
        #circumsolar brightness coefficient, F1
        f11 = self.brightness_coefficient(E, 'f11')
        f12 = self.brightness_coefficient(E, 'f12')
        f13 = self.brightness_coefficient(E, 'f13')
        F1 = max(0, f11 + f12 * delta + f13 * (pi * self.solar_zenith_angle() / 180))
        
        circumsolar_irradiance = Gsol_d * F1 * (a / b)
        
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
