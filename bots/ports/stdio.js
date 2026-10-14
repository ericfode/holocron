'use strict';
// serve() for running a port with Node. The arena's JavaScript intake replaces this file with its own (the same serve()
// over Javy's stdin and stdout), so nothing outside this folder ends up in the bundle.
module.exports = require('../../engine/stdio');
