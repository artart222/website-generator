# Troubleshooting Guide

This guide helps resolve common issues when using the Website Generator.

## Build Issues

### Build fails with template errors

**Problem:** Templates not found or syntax errors.

**Solutions:**
- Check `themes/` directory exists and contains layouts
- Verify `site-theme/` overrides have correct paths
- Ensure Django template syntax is valid
- Check template engine configuration in `config.yaml`

### Pages not generating

**Problem:** Content files not processed.

**Solutions:**
- Verify file extensions are supported (.md, etc.)
- Check collection configuration in `config.yaml`
- Ensure source directory paths are correct
- Look for content model validation errors

### Assets not copying

**Problem:** Static files missing in output.

**Solutions:**
- Check `build.asset_dirs` in config
- Verify asset file paths exist
- Ensure output directory is writable

## Configuration Issues

### Config validation errors

**Problem:** Invalid configuration format.

**Solutions:**
- Use `version: 2` for new projects
- Check YAML syntax with online validator
- Refer to [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for v1 to v2 upgrade
- Ensure required fields are present

### Theme not loading

**Problem:** Theme files not found.

**Solutions:**
- Check `theme.name` matches directory in `themes/`
- Verify theme manifest exists
- Check file permissions

## Runtime Issues

### Django runtime not starting

**Problem:** Runtime server fails to start.

**Solutions:**
- Run `python wg_runtime/manage.py migrate`
- Create superuser with `createsuperuser`
- Check database configuration
- Verify Python path includes runtime

### Catalog snapshot failing

**Problem:** Runtime data not fetching.

**Solutions:**
- Check `runtime.targets` configuration
- Verify runtime server is running
- Check network connectivity to runtime URL
- Validate API endpoints

## Plugin/Extension Issues

### Plugin not loading

**Problem:** Plugin not found or failing.

**Solutions:**
- Check plugin name in `config.yaml` matches class name
- Verify plugin inherits from `BasePlugin`
- Check import errors in logs
- Ensure plugin file is in `plugins/` directory

### Extension not working

**Problem:** Extension features not available.

**Solutions:**
- Check extension is in `extensions.enabled`
- Verify extension package is installed
- Check extension manifest format
- Look for registration hook errors

## Performance Issues

### Build taking too long

**Problem:** Slow generation.

**Solutions:**
- Reduce number of pages
- Check for inefficient templates
- Disable unused plugins
- Use runtime catalog snapshot instead of live queries

### Memory usage high

**Problem:** Out of memory errors.

**Solutions:**
- Process large sites in batches
- Check for circular references in data
- Reduce template complexity
- Use streaming for large files

## Getting Help

If issues persist:
1. Check build logs for error messages
2. Enable debug logging: `build.log_level: 10`
3. Verify Python version (3.10+)
4. Test with minimal config
5. Check GitHub issues for similar problems