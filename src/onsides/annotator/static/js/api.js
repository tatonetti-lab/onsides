const API = {
    async getTasks() {
        const r = await fetch('/api/tasks');
        return r.json();
    },

    async getTask(taskId) {
        const r = await fetch(`/api/tasks/${taskId}`);
        return r.json();
    },

    async getLabels(taskId, page = 1, perPage = 50, search = '', seed = 42) {
        const params = new URLSearchParams({ task_id: taskId, page, per_page: perPage, search, seed });
        const r = await fetch(`/api/labels?${params}`);
        return r.json();
    },

    async getLabel(taskId, setId) {
        const params = new URLSearchParams({ task_id: taskId });
        const r = await fetch(`/api/labels/${setId}?${params}`);
        return r.json();
    },

    async loadAnnotation(taskId, annotator, labelId) {
        const r = await fetch(`/api/annotations/${taskId}/${annotator}/${labelId}`);
        if (r.status === 200) {
            const data = await r.json();
            return data;
        }
        return null;
    },

    async saveAnnotation(taskId, annotator, labelId, doc) {
        await fetch(`/api/annotations/${taskId}/${annotator}/${labelId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(doc),
        });
    },

    async listAnnotations(taskId, annotator) {
        const r = await fetch(`/api/annotations/${taskId}/${annotator}`);
        return r.json();
    },

    async searchVocab(taskId, query) {
        const params = new URLSearchParams({ task_id: taskId, q: query });
        const r = await fetch(`/api/vocab/search?${params}`);
        return r.json();
    },
};
