# NPM package.json Reference

## Overview

This document provides a comprehensive reference for the npm package.json file format, including all possible fields, dependency types, version ranges, and workspace configuration. Based on official npm documentation and the 2024 schema specification.

**Official Documentation**: https://docs.npmjs.com/cli/v9/configuring-npm/package-json/
**JSON Schema**: https://github.com/SchemaStore/schemastore/blob/master/src/schemas/json/package.json
**Version Information**: npm CLI v9 (2024)
**Documentation Date**: September 15, 2025

## Complete package.json Structure

The package.json file must be valid JSON (not just a JavaScript object literal). Here's the complete structure with all possible fields:

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "A description of my package",
  "keywords": ["keyword1", "keyword2"],
  "homepage": "https://github.com/owner/project#readme",
  "bugs": {
    "url": "https://github.com/owner/project/issues",
    "email": "project@hostname.com"
  },
  "license": "MIT",
  "author": "Your Name <email@example.com> (http://example.com/)",
  "contributors": [
    "Name1 <email1@example.com>",
    "Name2 <email2@example.com>"
  ],
  "funding": {
    "type": "individual",
    "url": "http://example.com/donate"
  },
  "files": ["lib/", "bin/", "README.md"],
  "main": "index.js",
  "browser": "browser.js",
  "bin": {
    "myapp": "./cli.js"
  },
  "man": "./man/doc.1",
  "directories": {
    "lib": "lib/",
    "bin": "bin/",
    "man": "man/",
    "doc": "doc/"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/owner/project.git",
    "directory": "packages/my-package"
  },
  "scripts": {
    "start": "node index.js",
    "test": "jest",
    "build": "webpack",
    "prepare": "npm run build"
  },
  "config": {
    "port": "8080"
  },
  "dependencies": {
    "express": "^4.18.0"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  },
  "peerDependencies": {
    "react": "^18.0.0"
  },
  "peerDependenciesMeta": {
    "react": {
      "optional": true
    }
  },
  "bundleDependencies": ["renderized", "super-streams"],
  "optionalDependencies": {
    "fsevents": "^2.3.0"
  },
  "overrides": {
    "foo": "1.0.0"
  },
  "engines": {
    "node": ">=14.0.0",
    "npm": ">=6.0.0"
  },
  "os": ["darwin", "linux"],
  "cpu": ["x64", "ia32"],
  "private": true,
  "publishConfig": {
    "registry": "https://npm.internal.company.com/"
  },
  "workspaces": ["packages/*"]
}
```

## Core Required Fields

### name
- **Required for published packages**
- Must be ≤ 214 characters (including scope)
- Scoped packages can begin with dot/underscore: `@myorg/mypackage`
- No uppercase letters for new packages
- Cannot contain non-URL-safe characters

### version
- **Required for published packages**
- Must be parseable by node-semver
- Format: MAJOR.MINOR.PATCH
- Examples: `1.0.0`, `2.1.3-alpha.1`

## All Dependency Fields

### dependencies
**Purpose**: Packages required for production runtime
**Installation**: Automatically installed with `npm install`
**Use case**: Core functionality libraries

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "~4.17.21",
    "moment": "2.29.4",
    "axios": ">=1.0.0 <2.0.0"
  }
}
```

### devDependencies
**Purpose**: Packages needed only for development and testing
**Installation**: Installed locally but not in production
**Use case**: Build tools, test frameworks, linters

```json
{
  "devDependencies": {
    "jest": "^29.0.0",
    "webpack": "^5.74.0",
    "eslint": "^8.0.0",
    "typescript": "^4.8.0"
  }
}
```

### peerDependencies
**Purpose**: Specify compatibility with host packages (plugins)
**Installation**: NOT automatically installed (warnings emitted if missing)
**Use case**: React components, Babel plugins, framework extensions

```json
{
  "peerDependencies": {
    "react": "^17.0.0 || ^18.0.0",
    "react-dom": "^17.0.0 || ^18.0.0"
  }
}
```

### peerDependenciesMeta
**Purpose**: Provide metadata for peer dependencies
**Use case**: Mark peer dependencies as optional

```json
{
  "peerDependenciesMeta": {
    "react-dom": {
      "optional": true
    }
  }
}
```

### optionalDependencies
**Purpose**: Dependencies that won't break installation if they fail
**Installation**: Installed if possible, skipped if not
**Use case**: Platform-specific packages, performance enhancements

```json
{
  "optionalDependencies": {
    "fsevents": "^2.3.0",
    "chokidar": "^3.5.0"
  }
}
```

### bundleDependencies (or bundledDependencies)
**Purpose**: Bundle specific dependencies with the package
**Installation**: Included in tarball when package is packed
**Use case**: Offline development, specific version guarantees

```json
{
  "bundleDependencies": ["renderized", "super-streams"]
}
```

## Version Ranges and Semver

### Exact Versions
```json
{
  "dependencies": {
    "react": "18.2.0"
  }
}
```

### Caret Range (^) - Most Common
**Allows**: Compatible within same major version
**Example**: `^1.2.3` allows `>=1.2.3 <2.0.0`

```json
{
  "dependencies": {
    "express": "^4.18.0"  // Allows 4.18.1, 4.19.0, but not 5.0.0
  }
}
```

**Special behavior for 0.x versions**:
- `^0.13.0` allows `0.13.1` but not `0.14.0`
- `^0.0.3` allows only `0.0.3` (no updates)

### Tilde Range (~) - More Restrictive
**Allows**: Compatible within same minor version
**Example**: `~1.2.3` allows `>=1.2.3 <1.3.0`

```json
{
  "dependencies": {
    "lodash": "~4.17.21"  // Allows 4.17.22, but not 4.18.0
  }
}
```

### Comparison Operators
```json
{
  "dependencies": {
    "package-a": ">1.0.0",
    "package-b": ">=2.0.0",
    "package-c": "<3.0.0",
    "package-d": "<=2.9.9",
    "package-e": ">=1.0.0 <2.0.0"
  }
}
```

### Wildcard and Range Patterns
```json
{
  "dependencies": {
    "any-version": "*",
    "empty-string": "",
    "x-pattern": "1.2.x",
    "major-pattern": "2.x",
    "hyphen-range": "1.0.0 - 2.9999.9999",
    "or-range": "<1.0.0 || >=2.3.1 <2.4.5"
  }
}
```

### Git URLs as Dependencies
```json
{
  "dependencies": {
    "package-from-git": "git+ssh://git@github.com:npm/cli.git",
    "with-commit": "git+https://github.com/npm/cli.git#v1.0.27",
    "with-semver": "git+https://github.com/npm/cli.git#semver:^5.0"
  }
}
```

### GitHub Shorthand
```json
{
  "dependencies": {
    "express": "expressjs/express",
    "mocha": "mochajs/mocha#4727d357ea",
    "module": "user/repo#feature/branch"
  }
}
```

### Local Paths
```json
{
  "dependencies": {
    "local-package": "file:../local-package",
    "another-local": "file:./packages/another"
  }
}
```

### URLs as Dependencies
```json
{
  "dependencies": {
    "tarball-package": "http://example.com/package.tar.gz"
  }
}
```

## Workspaces Configuration

### Basic Workspaces Setup
**Purpose**: Monorepo management with npm workspaces
**Requirement**: Root package.json must have `"private": true`

```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": ["packages/*"]
}
```

### Advanced Workspaces Patterns
```json
{
  "name": "complex-monorepo",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*",
    "tools/cli",
    "libs/shared"
  ]
}
```

### Workspace Directory Structure
```
project-root/
├── package.json (root)
├── node_modules/
├── packages/
│   ├── package-a/
│   │   └── package.json
│   └── package-b/
│       └── package.json
└── apps/
    └── web-app/
        └── package.json
```

### Workspace Scripts
```json
{
  "scripts": {
    "build": "npm run build --workspaces",
    "test": "npm run test --workspaces",
    "build-web": "npm run build --workspace=web-app",
    "test-package-a": "npm run test --workspace=@myorg/package-a"
  }
}
```

## Key Differences Between Dependency Types

| Dependency Type | Production | Development | Peer Warning | Auto Install | Use Case |
|----------------|------------|-------------|--------------|--------------|-----------|
| `dependencies` | ✅ | ✅ | ❌ | ✅ | Runtime requirements |
| `devDependencies` | ❌ | ✅ | ❌ | ✅ (dev only) | Build tools, tests |
| `peerDependencies` | ✅ | ✅ | ✅ | ❌ | Plugin compatibility |
| `optionalDependencies` | ✅ | ✅ | ❌ | ⚠️ (if possible) | Nice-to-have features |
| `bundleDependencies` | ✅ | ✅ | ❌ | ✅ (bundled) | Offline/specific versions |

## Other Important Fields

### engines
Specify required Node.js and npm versions:
```json
{
  "engines": {
    "node": ">=14.0.0",
    "npm": ">=6.0.0"
  }
}
```

### os and cpu
Platform restrictions:
```json
{
  "os": ["darwin", "linux", "!win32"],
  "cpu": ["x64", "ia32", "!arm"]
}
```

### overrides
Force specific dependency versions:
```json
{
  "overrides": {
    "lodash": "4.17.21",
    "react": {
      ".": "18.2.0",
      "react-dom": "18.2.0"
    }
  }
}
```

### scripts
Lifecycle and custom commands:
```json
{
  "scripts": {
    "start": "node server.js",
    "build": "webpack --mode production",
    "test": "jest",
    "prepare": "npm run build",
    "preinstall": "node check-node-version.js",
    "postinstall": "node setup.js"
  }
}
```

## Best Practices

1. **Use semantic versioning** for your package versions
2. **Prefer caret ranges (^)** for most dependencies
3. **Use exact versions** only when necessary for stability
4. **Set `"private": true`** for internal packages and monorepos
5. **Use `peerDependencies`** for plugin architectures
6. **Document breaking changes** when bumping major versions
7. **Keep `devDependencies` separate** from production dependencies
8. **Use `engines`** to specify minimum Node.js version requirements

## Common Patterns

### React Component Library
```json
{
  "name": "@myorg/ui-components",
  "version": "1.2.3",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "peerDependencies": {
    "react": "^17.0.0 || ^18.0.0",
    "react-dom": "^17.0.0 || ^18.0.0"
  },
  "devDependencies": {
    "react": "^18.2.0",
    "typescript": "^4.8.0",
    "rollup": "^2.79.0"
  }
}
```

### CLI Tool
```json
{
  "name": "my-cli-tool",
  "version": "1.0.0",
  "bin": {
    "mycli": "./bin/cli.js"
  },
  "engines": {
    "node": ">=14.0.0"
  },
  "dependencies": {
    "commander": "^9.0.0",
    "chalk": "^4.1.2"
  }
}
```

### Monorepo Root
```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": ["packages/*", "apps/*"],
  "devDependencies": {
    "lerna": "^5.0.0",
    "jest": "^29.0.0",
    "typescript": "^4.8.0"
  },
  "scripts": {
    "build": "npm run build --workspaces",
    "test": "jest",
    "lint": "eslint packages apps"
  }
}
```

## Additional Resources

- [npm CLI Documentation](https://docs.npmjs.com/)
- [Semantic Versioning Specification](https://semver.org/)
- [npm Workspaces Guide](https://docs.npmjs.com/cli/v7/using-npm/workspaces/)
- [Package.json Schema](https://github.com/SchemaStore/schemastore/blob/master/src/schemas/json/package.json)
- [npm Semver Calculator](https://semver.npmjs.com/)