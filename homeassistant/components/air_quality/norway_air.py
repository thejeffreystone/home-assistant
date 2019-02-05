"""
Sensor for checking the air quality forecast around Norway.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/air_quality.norway_air/
"""
import logging

from datetime import timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.air_quality import (
    PLATFORM_SCHEMA, AirQualityEntity)
from homeassistant.const import (CONF_LATITUDE, CONF_LONGITUDE,
                                 CONF_NAME,
                                 CONF_SHOW_ON_MAP)
from homeassistant.helpers.aiohttp_client import async_get_clientsession


REQUIREMENTS = ['pyMetno==0.4.5']

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Air quality from " \
              "https://luftkvalitet.miljostatus.no/, " \
              "delivered by the Norwegian Meteorological Institute."
# https://api.met.no/license_data.html

CONF_FORECAST = 'forecast'

DEFAULT_FORECAST = 0
DEFAULT_NAME = 'Air quality Norway'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_FORECAST, default=DEFAULT_FORECAST): vol.Coerce(int),
    vol.Optional(CONF_LATITUDE): cv.latitude,
    vol.Optional(CONF_LONGITUDE): cv.longitude,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SHOW_ON_MAP, default=True): cv.boolean,
})

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the air_quality norway sensor."""
    forecast = config.get(CONF_FORECAST)
    latitude = config.get(CONF_LATITUDE, hass.config.latitude)
    longitude = config.get(CONF_LONGITUDE, hass.config.longitude)
    name = config.get(CONF_NAME)

    if None in (latitude, longitude):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return False

    coordinates = {
        'lat': str(latitude),
        'lon': str(longitude),
    }

    async_add_entities([AirSensor(name, coordinates,
                                  forecast, async_get_clientsession(hass),
                                  config.get(CONF_SHOW_ON_MAP)
                                  )],
                       True)


def round_state(func):
    """Round state."""
    def _decorator(self):
        res = func(self)
        if isinstance(res, float):
            return round(res, 2)
        return res
    return _decorator


class AirSensor(AirQualityEntity):
    """Representation of an Yr.no sensor."""

    def __init__(self, name, coordinates, forecast, session, show_on_map):
        """Initialize the sensor."""
        import metno
        self._name = name
        self._api = metno.AirQualityData(coordinates, forecast, session)
        self._attrs = {}
        if show_on_map:
            self._attrs[CONF_LATITUDE] = coordinates['lat']
            self._attrs[CONF_LONGITUDE] = coordinates['lon']

    @property
    def attribution(self) -> str:
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def device_state_attributes(self) -> dict:
        """Return other details about the sensor state."""
        return self._attrs

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    @round_state
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        return self._api.data.get('aqi')

    @property
    @round_state
    def nitrogen_dioxide(self):
        """Return the NO2 (nitrogen dioxide) level."""
        return self._api.data.get('no2_concentration')

    @property
    @round_state
    def ozone(self):
        """Return the O3 (ozone) level."""
        return self._api.data.get('o3_concentration')

    @property
    @round_state
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        return self._api.data.get('pm25_concentration')

    @property
    @round_state
    def particulate_matter_10(self):
        """Return the particulate matter 10 level."""
        return self._api.data.get('pm10_concentration')

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._api.units.get('pm25_concentration')

    async def async_update(self) -> None:
        """Update the sensor."""
        await self._api.update()

    @property
    def state_attributes(self):
        """Return the state attributes."""
        res = super().state_attributes
        res = dict() if res is None else res
        res['level'] = self._api.data.get('level')
        return res
