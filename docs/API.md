# Gmail Invoice Scanner API Documentation

## Authentication Flow

### 1. OAuth2 Authentication

The application uses OAuth2 for Gmail authentication. The flow is as follows:

1. User visits `/auth` endpoint
2. Application generates OAuth URL using Google credentials
3. User is redirected to Google consent screen
4. After consent, Google redirects to `/oauth2callback`
5. Application exchanges code for access token
6. Token is stored securely for future use

### 2. Email Processing

The email processing flow consists of:

1. Fetching emails using Gmail API
2. Filtering for invoices
3. Processing attachments
4. Extracting data using OpenAI
5. Storing results

## API Endpoints

### Authentication Endpoints

#### GET /auth
Initiates the OAuth flow

**Response:**
- Redirects to Google consent screen

#### GET /oauth2callback
Handles OAuth callback from Google

**Query Parameters:**
- `code`: Authorization code
- `state`: State parameter for security

**Response:**
- Redirects to home page on success
- Error message on failure

#### GET /revoke
Revokes current Gmail authorization

**Response:**
- Success/failure message

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

### Gmail API Scopes

The application requires the following Gmail API scopes:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.modify`

## Error Handling

The application implements comprehensive error handling:

1. Authentication Errors
   - Invalid credentials
   - Expired tokens
   - Missing permissions

2. API Errors
   - Rate limiting
   - Network issues
   - Service unavailability

3. Processing Errors
   - Invalid attachments
   - Failed extractions
   - Storage issues

## Security Considerations

1. Token Storage
   - Tokens are stored encrypted
   - Regular token rotation
   - Secure file permissions

2. API Access
   - Minimal scope usage
   - Rate limiting
   - Request validation

3. Data Protection
   - Secure attachment handling
   - Temporary file cleanup
   - Logging sanitization
