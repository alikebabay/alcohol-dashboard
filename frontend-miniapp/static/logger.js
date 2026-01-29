// logger.js
const LEVELS = { off: -1, error: 0, warn: 1, info: 2, debug: 3, trace: 4 };

const config = {
  level: "info",   // глобальный уровень
  modules: {},     // { state: true/false, editor: true/false, ... }
};

export function setLogLevel(level) {
  config.level = level;
}

export function enableModule(name) {
  config.modules[name] = true;
}

export function disableModule(name) {
  config.modules[name] = false;
}

function shouldLog(level, module) {
  if (config.level === "off") return false;
  if (LEVELS[level] > LEVELS[config.level]) return false;
  if (module in config.modules && config.modules[module] === false) return false;
  return true;
}

export function getLogger(moduleName) {
  return {
    error(msg, data) {
      if (shouldLog("error", moduleName))
        console.error(`[${moduleName}]`, msg, data ?? "");
    },
    warn(msg, data) {
      if (shouldLog("warn", moduleName))
        console.warn(`[${moduleName}]`, msg, data ?? "");
    },
    info(msg, data) {
      if (shouldLog("info", moduleName))
        console.log(`[${moduleName}]`, msg, data ?? "");
    },
    debug(msg, data) {
      if (shouldLog("debug", moduleName))
        console.log(`[${moduleName}]`, msg, data ?? "");
    },
    trace(msg, data) {
      if (shouldLog("trace", moduleName))
        console.log(`[${moduleName}]`, msg, data ?? "");
    },
  };
}
