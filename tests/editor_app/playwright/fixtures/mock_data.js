// tests/editor_app/playwright/fixtures/mock_data.js

export const MOCK_COMPONENTS_RESPONSE = {
    groups: [
        {
            id: 'network',
            name: 'Network Services',
            is_exclusive: false,
            components: [
                { id: 'pi-hole', name: 'Pi-hole' },
                { id: 'traefik', name: 'Traefik' }
            ]
        },
        {
            id: 'media',
            name: 'Media Servers',
            is_exclusive: true,
            components: [{ id: 'jellyfin', name: 'Jellyfin' }]
        }
    ]
};

export const MOCK_TRAEFIK_DETAILS = {
    name: 'Traefik',
    description: 'A modern reverse proxy and load balancer.',
    group: 'network',
    depends_on: [],
    conflicts_with: ['nginx-proxy-manager'],
    has_ui: true,
    has_configuration: true,
    has_traefik_support: false, // Traefik does not proxy itself
    traefik_internal_port: null,
    required_variables: [
        {
            id: 'TRAEFIK_DASHBOARD_USERS',
            label: 'Dashboard Credentials',
            description: 'Secure credentials for the Traefik dashboard.',
            type: 'password',
            default: '{{ DOTENV.TRAEFIK_DASHBOARD_USERS }}',
            source: '',
            required: 'always'
        },
        {
            id: 'ACME_EMAIL',
            label: 'ACME Email',
            description: 'Email for Let`s Encrypt SSL certificates.',
            type: 'string',
            default: '',
            source: 'dotenv',
            required: 'clean-install'
        }
    ]
};

export const MOCK_JELLYFIN_DETAILS = {
    name: 'Jellyfin',
    description: 'The Free Software Media System.',
    group: 'media',
    depends_on: ['traefik'],
    conflicts_with: [],
    has_ui: true,
    has_configuration: true,
    has_traefik_support: true,
    traefik_internal_port: 8096,
    required_variables: [
        {
            id: 'JELLYFIN_DATA_PATH',
            label: 'Jellyfin Data Path',
            description: 'Path to store Jellyfin configuration and data.',
            type: 'path',
            default: '{{ CONFIG_BASE_PATH }}/jellyfin/config',
            source: '',
            required: ''
        },
        {
            id: 'JELLYFIN_MEDIA_LOCATION',
            label: 'Media Location',
            description: 'Where is your media stored?',
            type: 'choice',
            default: 'nas',
            source: '',
            required: 'always',
            options: [
                { value: 'nas', label: 'Network Attached Storage (NAS)' },
                { value: 'usb', label: 'Attached USB Drive' }
            ]
        },
        {
            id: 'JELLYFIN_NAS_PATH',
            label: 'NAS Path',
            description: 'The full path to your media on the NAS.',
            type: 'path',
            default: '',
            source: '',
            required: '',
            depends_on: {
                id: 'JELLYFIN_MEDIA_LOCATION',
                value: 'nas'
            }
        }
    ]
};

export const MOCK_TRAEFIK_TEMPLATE = `# Docker Compose template for Traefik
services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
`;

export const MOCK_VALIDATION_FAILURE = {
    error: 'Validation failed: traefik conflicts with itself in the global component list.'
};
