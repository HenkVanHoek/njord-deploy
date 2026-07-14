# templates/gitlab/template-config/gitlab.rb
# This is the primary configuration file for GitLab.
# It is written in Ruby, so be careful with the syntax.

# --- CRITICAL SETTINGS ---
# This URL must be set to the address users will use to access GitLab.
# It is used to generate clone URLs and for many internal functions.
# We are using the HTTP port here, assuming a reverse proxy will handle HTTPS.
external_url 'http://{{ DOMAIN }}:{{ GITLAB_HTTP_PORT | default(10080) }}'

# --- SSH PORT CONFIGURATION ---
# If you use a non-standard SSH port (like 10022), you must inform GitLab.
gitlab_rails['gitlab_shell_ssh_port'] = {{ GITLAB_SSH_PORT | default(10022) }}

# --- RESOURCE MANAGEMENT (IMPORTANT FOR RASPBERRY PI) ---
# These settings are recommended to reduce GitLab's memory and CPU usage.
# Adjust them based on your Raspberry Pi model (e.g., 4GB vs 8GB RAM).

# Number of Unicorn workers (web server). By default, this is auto-detected.
# For a Pi, 2 is a safe starting point.
unicorn['worker_processes'] = 2

# Number of Sidekiq workers (background jobs).
sidekiq['concurrency'] = 5

# PostgreSQL database settings
postgresql['shared_buffers'] = "256MB" # Default is 256MB, can be lowered to 128MB if necessary.

# --- OPTIONAL FEATURES ---
# You can disable services you don't need to save resources.
# For example, to disable the container registry:
# registry['enable'] = false

# To disable Prometheus monitoring (saves a lot of memory):
prometheus_monitoring['enable'] = false

# --- EMAIL CONFIGURATION (EXAMPLE FOR INTERNAL PISELFHOSTING MAIL SERVER) ---
# These settings are managed by the web configurator.
# This example shows how to connect to another mail server container
# within the same Docker network.

# gitlab_rails['smtp_enable'] = true
# gitlab_rails['smtp_address'] = "mailserver" # The service name of your mail server container
# gitlab_rails['smtp_port'] = 25 # Use port 25 for unencrypted communication within the Docker network
# gitlab_rails['smtp_user_name'] = "gitlab@{{ DOMAIN }}" # An example username
# gitlab_rails['smtp_password'] = "a-strong-password" # The password for the user
# gitlab_rails['smtp_domain'] = "{{ DOMAIN }}" # The domain of the mail server
# gitlab_rails['smtp_authentication'] = "login"
#
# # Important: TLS is not required for communication within a trusted Docker network.
# # The reverse proxy handles encryption for the outside world.
# gitlab_rails['smtp_enable_starttls_auto'] = false
# gitlab_rails['smtp_tls'] = false
#
# gitlab_rails['gitlab_email_from'] = 'gitlab@{{ DOMAIN }}'
# gitlab_rails['gitlab_email_reply_to'] = 'noreply@{{ DOMAIN }}'
