FROM dhi.io/python:3.15.2-alpine3.24-dev AS build

# From requirements.txt rather than named here, because that is the file
# Dependabot reads: a new repwise release arrives as a pull request.
COPY requirements.txt /requirements.txt
RUN python3 -m venv /opt/repwise \
    && /opt/repwise/bin/pip install --no-cache-dir --requirement /requirements.txt \
    && /opt/repwise/bin/pip uninstall --yes pip

# The venv's interpreter is a symlink to the one that created it, which the
# runtime image has at the same path only while both stages are the same
# Python. Dependabot groups the two tags so that they move together.
FROM dhi.io/python:3.15.2-alpine3.24

COPY --from=build /opt/repwise /opt/repwise
COPY server.py /server.py

# Unbuffered, so that what a run prints reaches the pod's log when it happens.
ENV PATH=/opt/repwise/bin:$PATH \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "/server.py"]
