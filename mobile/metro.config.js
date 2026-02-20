const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

const parentDir = path.resolve(__dirname, '..');

// Allow Metro to resolve modules from the parent directory (for core/ imports)
config.watchFolders = [parentDir];

// Ensure node_modules are still found from the mobile dir
config.resolver.nodeModulesPaths = [path.resolve(__dirname, 'node_modules')];

// Map parent-dir packages so Metro can resolve them
config.resolver.extraNodeModules = {
  ...config.resolver.extraNodeModules,
  core: path.resolve(parentDir, 'core'),
};

module.exports = config;
