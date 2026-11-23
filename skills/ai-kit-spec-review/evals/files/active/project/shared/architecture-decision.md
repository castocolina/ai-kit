# Architecture decision: one cache per tenant

We keep one cache per tenant so that a noisy tenant cannot evict another tenant's entries.

Open point: the eviction limit per tenant is not chosen yet.
