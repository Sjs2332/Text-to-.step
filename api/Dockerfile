# Text-to-CAD API Server Container
# 
# Builds a production-ready API server with FreeCAD for geometry generation.
# Uses Python 3.11 on Debian Bookworm to match FreeCAD's system requirements.

FROM python:3.11-slim-bookworm

# Install system dependencies
# FreeCAD provides the native B-Rep kernel for geometry generation
# Git is needed for DXF importer library setup
RUN apt-get update && apt-get install -y \
    freecad \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# Running as non-root limits impact of potential container escapes
RUN useradd -m -s /bin/bash geometryuser

# Install DXF importer library for FreeCAD
# This extends FreeCAD's Draft module to support DXF file imports
RUN mkdir -p /usr/share/freecad/Mod/Draft/draftlibs && \
    git clone https://github.com/yorikvanhavre/Draft-dxf-importer.git /usr/share/freecad/Mod/Draft/draftlibs && \
    rm -rf /usr/share/freecad/Mod/Draft/draftlibs/.git && \
    touch /usr/share/freecad/Mod/Draft/draftlibs/__init__.py && \
    chown -R geometryuser:geometryuser /usr/share/freecad/Mod/Draft/draftlibs

WORKDIR /app

# Install Python dependencies
# Using --break-system-packages because Debian's Python packages conflict
# with pip-installed packages. This is safe in containerized environments.
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed -r requirements.txt

# Copy application code
COPY main.py pipeline.py ./
COPY lib ./lib

# Create temporary directories with proper permissions
RUN mkdir -p /tmp/geometry_renders && \
    chown -R geometryuser:geometryuser /tmp/geometry_renders && \
    chown -R geometryuser:geometryuser /app

# Set PYTHONPATH to include FreeCAD libraries and application code
# FreeCAD's Python bindings are in /usr/lib/freecad/lib on Debian
ENV PYTHONPATH=/usr/lib/freecad/lib:/app

# Switch to non-root user
USER geometryuser

# Expose API port
EXPOSE 8080

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
