# RFC 0042: Rate limiting for the public API

## Problem

Clients can send unlimited requests and starve other tenants.

## Proposal

Add a token bucket per API key: 100 requests per minute, refilled every second.

## Rollout

Enable it for all keys at once.
