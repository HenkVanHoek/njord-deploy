# --- Stage 1: Build the static website ---
FROM python:3.11-slim as builder

# Install MkDocs and the Material theme
RUN pip install mkdocs-material

WORKDIR /app

# Copy the MkDocs configuration file
COPY mkdocs.yml .

# Copy the source Markdown files prepared by SetupManager into the build context
COPY ./src-docs ./src-docs


# Run the build command. MkDocs will read mkdocs.yml, find the source files
# in ./src-docs, and generate the static site in the '/app/site' directory.
RUN mkdocs build

# --- Stage 2: Serve the static site with Nginx ---
FROM nginx:1.25-alpine

# Remove the default Nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy the generated static site from the builder stage
COPY --from=builder /app/site /usr/share/nginx/html

# Expose port 80 for the webserver
EXPOSE 80

# Command to start Nginx
CMD ["nginx", "-g", "daemon off;"]
