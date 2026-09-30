import { useCallback, useEffect, useState } from "react";
import { api, errorMessage, fetchAll } from "./api/client";

export function usePaged(path, filters = {}) {
  const [payload, setPayload] = useState({ count: 0, results: [] });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get(path, { params: { page, search, page_size: 10, ...filters } });
      setPayload(response.data.results ? response.data : { count: response.data.length, results: response.data });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [path, page, search, JSON.stringify(filters)]);

  useEffect(() => {
    load();
  }, [load]);

  return { rows: payload.results || [], count: payload.count || 0, page, setPage, search, setSearch, loading, error, reload: load, pages: Math.max(1, Math.ceil((payload.count || 0) / 10)) };
}

export function useOptions() {
  const [options, setOptions] = useState({ faculties: [], departments: [], sessions: [], semesters: [], courses: [], students: [], lecturers: [] });
  useEffect(() => {
    Promise.all([
      fetchAll("/faculties/"),
      fetchAll("/departments/"),
      fetchAll("/sessions/"),
      fetchAll("/semesters/"),
      fetchAll("/courses/"),
      fetchAll("/students/").catch(() => ({ results: [] })),
      fetchAll("/lecturers/").catch(() => ({ results: [] })),
    ]).then(([faculties, departments, sessions, semesters, courses, students, lecturers]) => {
      const list = (payload) => payload.results || payload;
      setOptions({
        faculties: list(faculties),
        departments: list(departments),
        sessions: list(sessions),
        semesters: list(semesters),
        courses: list(courses),
        students: list(students),
        lecturers: list(lecturers),
      });
    });
  }, []);
  return options;
}
