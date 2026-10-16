# 本地架构集成验收

日期：2026-10-07。范围：只读工作台、既有证据同步、派生知识引用。未调用目标模型或研究模型。

## 实际执行

- `python -m unittest discover -s workbench/apertus-workbench/tests -p test_local_lab.py -v`：4/4通过；临时离线fixture覆盖只读/不存在账本、损坏证据、HTTP边界、汇总幂等与编辑保护。
- 项目 Bun 执行 `workbench/apertus-workbench/tests`：3/3通过，14 assertions；覆盖既有基础测试和新幂等摘要导入。
- `python scripts/lab.py sync` 连续执行两次：均成功；2条Memory、2张运行草稿、1张配对汇总，第二次不增加数量。
- `python scripts/lab.py status`：docker-mvp为2次completed运行，6探索+12确认，not_supported；development未创建；3张Wiki页面引用current。
- 同步前后原账本SHA256相同：`C04E55A65532FA9F54E79D6B72E36BBDDA17C5B29F26F53689A9E9F99DE006DB`。
- 本地服务启动在127.0.0.1:8765；浏览器显示2运行/18调用/18符合预期/0错误。点击探索运行，逐条显示en/de/fr输入、实际BLUE回答和exact_stripped_match判定依据。

## 边界

页面无写入或模型调度接口；SQLite使用mode=ro及query_only。同步使用单独进程锁，已有派生内容不一致则拒绝覆盖。candidate仅为知识草稿状态；not_supported保持不变。

完整Wiki应用API/Web、完整BreachWeave运行时及研究Agent尚未验收。未修改上游子仓库、冻结发布runner、原始账本或用户暂存状态；未执行新真实实验或提交发布。
