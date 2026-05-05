export const shell = {
  sidebar: {
    eyebrow: "本地优先资产工作台",
    title: "资产工作台",
    expand: "展开侧栏",
    collapse: "收起侧栏",
  },
  topbar: {
    eyebrow: "Windows 本地资产工作台",
    fallbackTitle: "工作台",
    pages: {
      home: "首页",
      onboarding: "引导",
      search: "搜索",
      files: "文件",
      books: "图书",
      software: "软件",
      media: "媒体库",
      games: "游戏",
      recent: "最近导入",
      tags: "标签",
      collections: "集合",
      settings: "设置",
    },
    backend: {
      connected: "已连接",
      disconnected: "未连接",
    },
    details: {
      show: "显示详情",
      hide: "隐藏详情",
    },
  },
  desktopTitleBar: {
    windowTitle: "资产工作台窗口标题",
    appTitle: "资产工作台",
    minimize: "最小化窗口",
    maximize: "最大化窗口",
    restore: "还原窗口",
    close: "关闭窗口",
  },
} as const;
