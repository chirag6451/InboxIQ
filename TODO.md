# InboxIQ TODO List

## Security & Configuration
- [ ] Create new OAuth credentials in Google Cloud Console (old ones were exposed)
- [ ] Implement web-based configuration endpoint `/config`
  - [ ] Add configuration form UI with all settings from config.py
  - [ ] Implement save/update functionality
  - [ ] Add validation for email formats and required fields
  - [ ] Add proper error handling and success messages
  - [ ] Ensure configuration changes are persisted
  - [ ] Add authentication check for config access

## Features
- [ ] Complete web-based configuration interface
  - [ ] Email category management
  - [ ] User details configuration
  - [ ] Calendar settings
  - [ ] Notification preferences
  - [ ] Email forwarding rules

## Testing
- [ ] Add tests for configuration endpoint
- [ ] Add validation tests for configuration changes
- [ ] Test configuration persistence

## Documentation
- [ ] Add API documentation for configuration endpoint
- [ ] Update README with configuration interface usage
- [ ] Document configuration options and their effects

## Security Audit
- [ ] Regular check for sensitive data in codebase
- [ ] Implement rate limiting for configuration endpoint
- [ ] Add audit logging for configuration changes
