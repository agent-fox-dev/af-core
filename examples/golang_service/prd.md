Create a simple golang service endpoint that in the beginning only has a "ping" endpoint. 
Additionally, it has the typical health and uptime monitoring endpoints a deployment on Kubernetes expexcts.

The service should use the golang "Echo" framework and it's typical handlers for e.g. logging, error handling and security.

Typical golang project layout applies:
- cmd/ for entry points
- internal/ for anything that is purely internal code and should not be used by others
- every reusable code that can be used by other projects is in dedicated folders in the repo root. Example: "api/" or "auth/".
