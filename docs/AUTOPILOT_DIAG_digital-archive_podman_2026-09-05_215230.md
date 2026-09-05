# Autopilot Diagnostic Report: `digital-archive`

- **Timestamp:** 2026-09-05 21:52:30
- **Mode:** LXC
- **Engine:** PODMAN
- **Summary:** Package deployment failed: non-zero return code | stderr: Failed to connect to bus: No medium found
Failed to connect to bus: No medium found
Traceback (most recent call last):
  File "/usr/bin/podman-compose", line 33, in <module>
    sys.exit(load_entry_point('podman-compose==1.0.3', 'console_scripts', 'podman-compose')())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 1775, in main
    podman_compose.run()
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 1024, in run
    cmd(self, args)
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 1248, in wrapped
    return func(*args, **kw)
           ^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 1415, in compose_up
    podman_args = container_to_args(compose, cnt, detached=args.detach)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 645, in container_to_args
    assert_cnt_nets(compose, cnt)
  File "/usr/lib/python3/dist-packages/podman_compose.py", line 558, in assert_cnt_nets
    net_desc = nets[net] or {}
               ~~~~^^^^^
KeyError: "njorddeploy_net={'aliases': ['paperless-broker', 'njorddeploy-paperless-broker']}"
- **DNS Enabled:** True
- **Disk Free:** 56466 MB
- **Recommended Action:**

## Failing Components

## Container Log Excerpts
