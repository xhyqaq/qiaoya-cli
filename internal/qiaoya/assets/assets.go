package assets

import "embed"

// FS contains the files installed into agent skill/rule locations.
//
//go:embed skills/qiaoya/SKILL.md skills/qiaoya/references/* rules/*
var FS embed.FS
