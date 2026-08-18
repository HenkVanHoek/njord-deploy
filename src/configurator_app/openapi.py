"""OpenAPI 3.0 specification provider for NjordDeploy Configurator REST API.

Provides structured metadata for interactive Swagger UI documentation and
external automated consumers / AI coding agents.
"""

from typing import Any, Dict


def get_openapi_spec() -> Dict[str, Any]:
    """Returns the complete OpenAPI 3.0.3 specification for NjordDeploy."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "NjordDeploy Configurator REST API",
            "description": (
                "High-performance REST API for headless deployment "
                "orchestration, Agentic DevOps, Proxmox VE container/VM "
                "provisioning, pre-flight conflict safety analysis, "
                "and real-time SSE log streaming."
            ),
            "version": "0.5.24",
            "contact": {
                "name": "NjordDeploy Project",
                "url": "https://njorddeploy.com",
            },
            "license": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            },
        },
        "servers": [
            {
                "url": "/",
                "description": "Current Configurator Server",
            },
            {
                "url": "http://localhost:5001",
                "description": "Local Development / Production Instance",
            },
        ],
        "tags": [
            {
                "name": "Components & Metadata",
                "description": ("Service registry, templates, packages, and variables"),
            },
            {
                "name": "Discovery & Inspection",
                "description": ("Network scanning, device snapshotting, and hardware"),
            },
            {
                "name": "Conflict Analysis",
                "description": (
                    "Pre-flight port, volume, and resource conflict checks"
                ),
            },
            {
                "name": "Deployment & Streaming",
                "description": ("Artifact generation, execution, SSE logs, and health"),
            },
            {
                "name": "Proxmox Orchestration",
                "description": ("Proxmox VE LXC container and QEMU VM provisioning"),
            },
            {
                "name": "Engine & Settings",
                "description": ("Container runtime, repository sync, and environment"),
            },
        ],
        "paths": {
            "/api/components": {
                "get": {
                    "tags": ["Components & Metadata"],
                    "summary": "Retrieve all registered software components",
                    "description": (
                        "Returns a dictionary of all available services from "
                        "the single source of truth."
                    ),
                    "responses": {
                        "200": {
                            "description": (
                                "Map of component ID to metadata definition."
                            ),
                            "content": {
                                "application/json": {
                                    "example": {
                                        "grafana": {
                                            "id": "grafana",
                                            "name": "Grafana",
                                            "category": "Monitoring",
                                            "ports": ["3000:3000/tcp"],
                                        }
                                    }
                                }
                            },
                        },
                        "500": {"description": "Internal server error."},
                    },
                }
            },
            "/get-available-software": {
                "post": {
                    "tags": ["Components & Metadata"],
                    "summary": "List available software and packages",
                    "responses": {
                        "200": {
                            "description": ("List of available software and packages."),
                        }
                    },
                }
            },
            "/get-software-groups": {
                "get": {
                    "tags": ["Components & Metadata"],
                    "summary": "Get software categories and ordering rules",
                    "responses": {
                        "200": {"description": "Categorized software groups."}
                    },
                }
            },
            "/get-required-variables": {
                "post": {
                    "tags": ["Components & Metadata"],
                    "summary": "Get required environment variables",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "selected_components": [
                                        "grafana",
                                        "nextcloud",
                                    ]
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Dictionary of required variables."},
                        "400": {"description": "Invalid input payload."},
                    },
                }
            },
            "/validate-selection": {
                "post": {
                    "tags": ["Components & Metadata"],
                    "summary": "Validate component template files on disk",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "selected_components": [
                                        "adguard-home",
                                        "grafana",
                                    ]
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Selection is valid."},
                        "400": {"description": "Missing template or config files."},
                    },
                }
            },
            "/scan-pis": {
                "post": {
                    "tags": ["Discovery & Inspection"],
                    "summary": "Discover target hosts across local network",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "discovery_method": "direct_ip",
                                    "direct_target_ip": "192.168.178.150",
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "List of discovered target hosts."},
                        "400": {"description": "Invalid discovery parameters."},
                    },
                }
            },
            "/get-device-details": {
                "post": {
                    "tags": ["Discovery & Inspection"],
                    "summary": "Inspect remote host hardware and OS details",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "ip": "192.168.178.150",
                                    "username": "root",
                                    "password": "TargetPassword123",
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Hardware and OS details snapshot."},
                        "400": {"description": "Authentication or SSH error."},
                    },
                }
            },
            "/api/v1/system/analyze": {
                "post": {
                    "tags": ["Conflict Analysis"],
                    "summary": "Perform pre-flight safety conflict analysis",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "is_reinstallation": False,
                                    "devices": [
                                        {
                                            "ip": "192.168.178.150",
                                            "username": "root",
                                            "password": "SecretPassword",
                                        }
                                    ],
                                    "components": [
                                        {
                                            "id": "grafana",
                                            "name": "Grafana",
                                            "ports": ["3000:3000/tcp"],
                                            "volumes": [
                                                "/opt/grafana/data:" "/var/lib/grafana"
                                            ],
                                        }
                                    ],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Safety analysis completed.",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "internal_conflicts": [],
                                        "external_conflicts": {
                                            "ports": [],
                                            "volumes": [],
                                        },
                                        "resource_warnings": [],
                                    }
                                }
                            },
                        },
                        "400": {"description": "Blocking conflict detected."},
                    },
                }
            },
            "/start-installation": {
                "post": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Generate deployment staging artifacts",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "selected_components": ["grafana"],
                                    "devices": [
                                        {
                                            "ip": "192.168.178.150",
                                            "username": "root",
                                            "password": "SecretPassword",
                                        }
                                    ],
                                    "env_vars": {
                                        "GF_SECURITY_ADMIN_PASSWORD": ("AdminPassword")
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Artifacts generated in staging."},
                        "400": {"description": "Generation failure."},
                    },
                }
            },
            "/deploy-configuration": {
                "post": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Initiate asynchronous SSH deployment to host",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "output_path": (
                                        "/opt/njorddeploy/staging/session_1"
                                    ),
                                    "devices": [
                                        {
                                            "ip": "192.168.178.150",
                                            "username": "root",
                                            "password": "SecretPassword",
                                        }
                                    ],
                                    "selected_components_data": [
                                        {"id": "grafana", "name": "Grafana"}
                                    ],
                                    "global_vars": {
                                        "GF_SECURITY_ADMIN_PASSWORD": ("AdminPassword")
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "202": {
                            "description": "Deployment task accepted.",
                            "content": {
                                "application/json": {
                                    "example": {"task_id": "a1b2c3d4e5f67890"}
                                }
                            },
                        },
                        "400": {"description": "Pre-deployment conflict error."},
                    },
                }
            },
            "/stream-deployment/{target_task_id}": {
                "get": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Stream live deployment logs via SSE",
                    "parameters": [
                        {
                            "name": "target_task_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": ("Hexadecimal task ID returned by deploy."),
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "SSE event stream of live logs.",
                            "content": {"text/event-stream": {}},
                        }
                    },
                }
            },
            "/task-status/{target_task_id}": {
                "get": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Poll status and log snapshot of deployment task",
                    "parameters": [
                        {
                            "name": "target_task_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Task status and logs."},
                        "404": {"description": "Task ID not found."},
                    },
                }
            },
            "/api/deployment/{target_task_id}/evaluate": {
                "post": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Run post-deployment health evaluation",
                    "parameters": [
                        {
                            "name": "target_task_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "example": {
                                    "component_name": "grafana",
                                    "use_ai": True,
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Health evaluation report."},
                        "404": {"description": "Task not found."},
                    },
                }
            },
            "/get-container-logs": {
                "post": {
                    "tags": ["Deployment & Streaming"],
                    "summary": "Fetch live container logs via SSH",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "ip": "192.168.178.150",
                                    "username": "root",
                                    "password": "SecretPassword",
                                    "container_name": "njorddeploy-grafana",
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Raw container logs."},
                        "400": {"description": "Connection or parameters error."},
                        "404": {"description": "Container not running."},
                    },
                }
            },
            "/api/proxmox/create-lxc": {
                "post": {
                    "tags": ["Proxmox Orchestration"],
                    "summary": "Create and provision a clean Debian LXC",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "hostname": "ct-grafana",
                                    "cores": 4,
                                    "memory": 4096,
                                    "storage_name": "local-lvm",
                                    "storage_size": "20",
                                    "node": "pve",
                                    "password": "SecurePassword123!",
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": ("Container provisioned and IP assigned."),
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "ip": "192.168.178.185",
                                        "vmid": 120,
                                        "hostname": "ct-grafana",
                                        "username": "root",
                                    }
                                }
                            },
                        },
                        "400": {"description": "Configuration or template error."},
                        "409": {
                            "description": (
                                "Duplicate hostname or stale container pool."
                            )
                        },
                        "500": {"description": "Proxmox provisioning error."},
                    },
                }
            },
            "/api/proxmox/list-targets": {
                "post": {
                    "tags": ["Proxmox Orchestration"],
                    "summary": "List all active LXCs and VMs on Proxmox node",
                    "responses": {"200": {"description": "List of Proxmox targets."}},
                }
            },
            "/api/proxmox/start-target": {
                "post": {
                    "tags": ["Proxmox Orchestration"],
                    "summary": "Start a stopped target and wait for IP",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "vmid": 120,
                                    "type": "lxc",
                                    "node": "pve",
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Target online with IPv4 address."}
                    },
                }
            },
            "/api/engine-status": {
                "get": {
                    "tags": ["Engine & Settings"],
                    "summary": "Get active container runtime and sync status",
                    "responses": {
                        "200": {
                            "description": "Active container engine details.",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "engine": "docker",
                                        "is_docker": True,
                                        "is_podman": False,
                                        "supported_engines": [
                                            "docker",
                                            "podman",
                                        ],
                                        "is_remote_sync_enabled": True,
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/engine-switch": {
                "post": {
                    "tags": ["Engine & Settings"],
                    "summary": "Switch active container engine dynamically",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {"example": {"engine": "podman"}}
                        },
                    },
                    "responses": {
                        "200": {"description": "Engine successfully switched."},
                        "400": {"description": "Invalid engine specified."},
                    },
                }
            },
            "/api/validate-repo": {
                "post": {
                    "tags": ["Engine & Settings"],
                    "summary": "Validate connection for remote repository",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "example": {
                                    "url": (
                                        "https://github.com/HenkVanHoek/"
                                        "njord-deploy-components.git"
                                    ),
                                    "branch": "main",
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Repository connection is valid."},
                        "400": {"description": "Validation failed."},
                    },
                }
            },
        },
    }
