import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { TaskCreatePage } from "./pages/TaskCreatePage";
import { TaskChatPage } from "./pages/TaskChatPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { TaskListPage } from "./pages/TaskListPage";
import { TaskLogsPage } from "./pages/TaskLogsPage";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<TaskCreatePage />} />
        <Route path="/tasks" element={<TaskListPage />} />
        <Route path="/tasks/:taskId/chat" element={<TaskChatPage />} />
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="/tasks/:taskId/logs" element={<TaskLogsPage />} />
        <Route path="*" element={<Navigate replace to="/" />} />
      </Routes>
    </AppLayout>
  );
}
