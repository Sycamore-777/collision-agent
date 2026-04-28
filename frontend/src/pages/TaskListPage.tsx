import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { fetchTasks } from "../services/api";
import type { TaskSummary } from "../types";
import { formatDateTime } from "../utils/labels";

export function TaskListPage() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  async function loadTasks() {
    setLoading(true);
    const items = await fetchTasks();
    setTasks(items);
    setLoading(false);
  }

  useEffect(() => {
    void loadTasks();
  }, []);

  const filtered = tasks.filter((task) => (filter === "all" ? true : task.status === filter));

  return (
    <Panel
      title="任务列表"
      subtitle="按状态筛选会合任务，进入详情页查看报告、证据链和模型审计。"
      actions={
        <div className="inline-actions">
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">全部状态</option>
            <option value="pending">待处理</option>
            <option value="running">运行中</option>
            <option value="succeeded">已完成</option>
            <option value="manual_review">待人工复核</option>
            <option value="failed">失败</option>
          </select>
          <button onClick={() => void loadTasks()} type="button">
            刷新
          </button>
        </div>
      }
    >
      {loading ? <p className="muted">正在加载任务列表...</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>状态</th>
            <th>风险</th>
            <th>事件数</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          {!loading && !filtered.length ? (
            <tr>
              <td className="muted" colSpan={5}>暂无任务数据。</td>
            </tr>
          ) : null}
          {filtered.map((task) => (
            <tr key={task.task_id}>
              <td>
                <Link to={`/tasks/${task.task_id}`}>{task.task_id}</Link>
              </td>
              <td>
                <StatusBadge value={task.status} />
              </td>
              <td>
                <StatusBadge value={task.latest_risk_level} />
              </td>
              <td>{task.event_count}</td>
              <td>{formatDateTime(task.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
