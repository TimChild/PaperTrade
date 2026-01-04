#!/bin/bash
export CLERK_SECRET_KEY="sk_test_pqsD1P2H5GX52hNupaIUE4GLhcvtHGK5fs9KI4TX1O"
export VITE_CLERK_PUBLISHABLE_KEY="pk_test_YWxsb3dlZC1jcmF3ZGFkLTI2LmNsZXJrLmFjY291bnRzLmRldiQ"
export E2E_CLERK_USER_USERNAME="e2e_test_user"
export E2E_CLERK_USER_PASSWORD="TestPassword123!"
npx playwright test "$@"
