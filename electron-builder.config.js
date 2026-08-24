module.exports = {
  appId: "com.datia.app",
  productName: "Dat.ia",
  directories: {
    output: "dist",
    buildResources: "assets"
  },
  files: [
    "dist/**/*",
    "dist-electron/**/*",
    "public/**/*",
    "node_modules/**/*",
    "package.json"
  ],
  win: {
    target: [
      {
        target: "portable",
        arch: ["x64"]
      }
    ]
  },
  portable: {
    artifactName: "Datia-${version}.exe"
  }
};
