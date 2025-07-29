# Remove Authentication - Ultrathink Plan

## Objective
Remove all authentication, user management, and access restrictions from the trading platform since it's meant for local use only.

## Phase 1: Backend Authentication Removal

### 1.1 Remove Auth Dependencies
- [x] Remove get_current_user dependency from all endpoints
- [x] Remove get_current_active_user dependency
- [x] Remove get_admin_user dependency
- [x] Remove Depends imports for auth

### 1.2 Simplify Account Endpoints
- [x] Remove /account/login endpoint
- [x] Remove /account/me endpoint
- [x] Remove /account/api-keys endpoint (if auth-protected)
- [x] Make /account/balance public
- [x] Make /account/trading-fees public

### 1.3 Simplify Trading Endpoints
- [x] Make all trading endpoints public (already public)
- [x] Remove auth checks from order placement (none found)
- [x] Remove auth checks from position management (none found)

### 1.4 Remove Auth Infrastructure
- [x] Delete auth.py endpoint file
- [x] Delete user_service.py
- [x] Remove OAuth2PasswordBearer from security.py
- [x] Remove JWT token generation/validation
- [x] Remove password hashing utilities

### 1.5 Update Models
- [x] Remove LoginRequest model
- [x] Remove LoginResponse model
- [x] Remove user-related fields from responses

## Phase 2: Frontend Authentication Removal

### 2.1 Remove Auth Token Handling
- [x] Remove auth token from localStorage (removed interceptor)
- [x] Remove Authorization header from API requests
- [x] Remove auth interceptors from axios

### 2.2 Remove Login UI
- [x] Remove login page/modal (none found)
- [x] Remove logout functionality (none found)
- [x] Remove user profile components (none found)
- [x] Remove auth guards from routes (none found)

### 2.3 Update API Client
- [x] Remove login/logout API calls
- [x] Remove token refresh logic (none found)
- [x] Remove 401 error handling redirects
- [x] Simplify error handling

### 2.4 Remove Auth State
- [x] Remove auth context/state (none found)
- [x] Remove user state management (none found)
- [x] Remove auth-related hooks (none found)

## Phase 3: Configuration Updates

### 3.1 Backend Configuration
- [x] Remove SECRET_KEY from config (if only used for JWT)
- [x] Remove ACCESS_TOKEN_EXPIRE_MINUTES
- [x] Remove ALGORITHM setting
- [x] Update CORS to allow all origins for local use

### 3.2 Frontend Configuration
- [x] Remove auth-related environment variables (none found)
- [x] Update API client configuration
- [x] Remove auth-related dependencies (none found)

## Phase 4: Dependency Cleanup

### 4.1 Backend Dependencies
- [x] Remove python-jose[cryptography]
- [x] Remove passlib[bcrypt]
- [x] Remove python-multipart (if only for OAuth2)
- [x] Update requirements.txt

### 4.2 Frontend Dependencies
- [x] Remove any auth-related npm packages (none found)
- [x] Update package.json (no changes needed)

## Phase 5: Testing

### 5.1 API Testing
- [x] Test all market endpoints work without auth
- [x] Test trading endpoints work without auth
- [x] Test account endpoints work without auth
- [x] Test WebSocket connections work without auth

### 5.2 Frontend Testing
- [ ] Verify app loads without login
- [ ] Test all features are accessible
- [ ] Verify no auth errors appear
- [ ] Check console for auth-related warnings

## Phase 6: Documentation

### 6.1 Update Documentation
- [x] Remove auth setup instructions (no auth sections found)
- [x] Remove user management docs (no user docs found)
- [x] Update API documentation (accessible at /docs)
- [x] Add note about local-only usage

### 6.2 Update README
- [x] Remove authentication section (no auth section existed)
- [x] Clarify local-only nature
- [x] Update getting started guide