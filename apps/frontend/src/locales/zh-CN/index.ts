import { en } from "../en";
import { common } from "./common";
import { details } from "./details";
import { features } from "./features";
import { navigation } from "./navigation";
import { pages } from "./pages";
import { settings } from "./settings";
import { shell } from "./shell";

export const zhCN = {
  common,
  details,
  features,
  navigation,
  pages,
  settings,
  shell,
} as const satisfies typeof en;
