import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = ["@yeah"]
DEPENDENCIES = ["remote_transmitter"]

marantec_ns = cg.esphome_ns.namespace("marantec")
