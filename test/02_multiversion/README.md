# 02 多版本 CDM + 事件聚合

同时上传 `cdm_v1.json` 和 `cdm_v2.json`。两个文件使用同一个 `conjunction_id`，系统应聚合为同一事件线程，并以最新版本作为结果视图。
