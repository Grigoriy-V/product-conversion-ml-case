# Lifecycle

Supervisor writes a bounded task. Worker appends `started`, executes only the
scope, then appends one terminal event with actual evidence. Supervisor alone
adds `reviewed`. The helper generates UTC timestamps and appends at EOF.
