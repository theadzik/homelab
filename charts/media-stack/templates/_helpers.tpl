{{/*
Expand the name of the chart.
*/}}
{{- define "media-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "media-stack.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "media-stack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels - includes all Helm recommended labels except component-specific ones
Usage: include "media-stack.labels" .
*/}}
{{- define "media-stack.labels" -}}
helm.sh/chart: {{ include "media-stack.chart" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ include "media-stack.name" . }}
{{- end }}

{{/*
Selector labels for a service component
Usage: include "media-stack.selectorLabels" (dict "component" "jellyfin" "context" $)
*/}}
{{- define "media-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app.kubernetes.io/part-of: {{ include "media-stack.name" .context }}
{{- end }}

{{/*
Component labels - combines common labels with component-specific labels
Usage: include "media-stack.componentLabels" (dict "component" "jellyfin" "context" $)
*/}}
{{- define "media-stack.componentLabels" -}}
{{ include "media-stack.labels" .context }}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
{{- end }}
