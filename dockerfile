FROM odoo:17.0

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libldap2-dev \
    libsasl2-dev \
    python3-pip \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for Google Drive integration
RUN pip3 install --no-cache-dir \
    google-auth \
    google-auth-oauthlib \
    google-api-python-client

USER odoo