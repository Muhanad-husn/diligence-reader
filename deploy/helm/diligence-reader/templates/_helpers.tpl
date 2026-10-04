{{/* The release's full name, cut to the 63 characters a Kubernetes name allows. */}}
{{- define "diligence-reader.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "diligence-reader.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "diligence-reader.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: api
{{- end -}}

{{- define "diligence-reader.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}

{{- define "diligence-reader.claim" -}}
{{- .Values.runs.existingClaim | default (printf "%s-runs" (include "diligence-reader.fullname" .)) -}}
{{- end -}}

{{/* The volumes of the API pod, which every run Job gets too. */}}
{{- define "diligence-reader.volumes" -}}
- name: runs
  persistentVolumeClaim:
    claimName: {{ include "diligence-reader.claim" . }}
{{- with .Values.extraVolumes }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* The mounts of the API container, which every run Job's container gets too. */}}
{{- define "diligence-reader.volumeMounts" -}}
- name: runs
  mountPath: /app/runs
{{- with .Values.extraVolumeMounts }}
{{ toYaml . }}
{{- end }}
{{- end -}}
