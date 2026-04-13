daemonize = false
authentication = "internal_plain"
storage = "internal"
c2s_require_encryption = false
allow_unencrypted_plain_auth = true
allow_registration = true
sasl_mechanisms = { "PLAIN" }
modules_enabled = { "roster", "saslauth", "disco", "register", "ping" }
VirtualHost "localhost"
    allow_registration = true
    c2s_require_encryption = false
    allow_unencrypted_plain_auth = true
    authentication = "internal_plain"
    sasl_mechanisms = { "PLAIN" }