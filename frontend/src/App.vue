<template>
  <router-view />
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.page-card { margin-bottom: 16px; }

/* ===== 移动端竖屏适配（≤768px） ===== */
/* 对话框不超出手机视口（max-width 可约束 el-dialog 的内联固定宽度） */
@media (max-width: 768px) {
  .el-dialog {
    max-width: 92vw;
  }
  .el-message-box {
    max-width: 92vw;
  }
  /* 表格内边距收紧，横向滚动更省空间 */
  .el-table .el-table__cell {
    padding: 6px 0;
  }
  .el-table {
    font-size: 13px;
  }
  /* 内联表单控件在手机上占满整行，避免挤压 */
  .el-form--inline .el-form-item {
    width: 100%;
    margin-right: 0;
  }
  .el-form--inline .el-form-item .el-input,
  .el-form--inline .el-form-item .el-select,
  .el-form--inline .el-form-item .el-date-editor,
  .el-form--inline .el-form-item .el-input-number {
    width: 100% !important;
  }
  .el-card__body {
    padding: 12px;
  }
  /* el-message 不超出屏幕 */
  .el-message {
    max-width: 92vw;
  }
}
</style>
