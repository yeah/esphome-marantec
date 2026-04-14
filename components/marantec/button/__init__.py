import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button, remote_transmitter
from esphome.const import CONF_ID
from .. import marantec_ns

DEPENDENCIES = ["remote_transmitter"]

CONF_TRANSMITTER_ID = "transmitter_id"
CONF_CODE = "code"
CONF_REPEAT = "repeat"

MarantecButton = marantec_ns.class_("MarantecButton", button.Button, cg.Component)

CONFIG_SCHEMA = button.button_schema(MarantecButton).extend(
    {
        cv.Required(CONF_TRANSMITTER_ID): cv.use_id(
            remote_transmitter.RemoteTransmitterComponent
        ),
        cv.Required(CONF_CODE): cv.hex_uint64_t,
        cv.Optional(CONF_REPEAT, default=4): cv.int_range(min=1, max=20),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = await button.new_button(config)
    await cg.register_component(var, config)

    transmitter = await cg.get_variable(config[CONF_TRANSMITTER_ID])
    cg.add(var.set_transmitter(transmitter))
    cg.add(var.set_code(config[CONF_CODE]))
    cg.add(var.set_repeat(config[CONF_REPEAT]))
