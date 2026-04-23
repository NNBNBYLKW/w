import type { SVGProps } from "react";

import BooksIcon from "../../../assets/icons/navigation/books.svg?react";
import CloseIcon from "../../../assets/icons/navigation/close.svg?react";
import CollectionsIcon from "../../../assets/icons/navigation/collections.svg?react";
import ConnectionIcon from "../../../assets/icons/navigation/connection.svg?react";
import FilesIcon from "../../../assets/icons/navigation/files.svg?react";
import GamesIcon from "../../../assets/icons/navigation/games.svg?react";
import Maxmize1Icon from "../../../assets/icons/navigation/maxmize1.svg?react";
import Maxmize2Icon from "../../../assets/icons/navigation/maxmize2.svg?react";
import MediaIcon from "../../../assets/icons/navigation/media.svg?react";
import MinimizeIcon from "../../../assets/icons/navigation/minimize.svg?react";
import OnboardingIcon from "../../../assets/icons/navigation/onboarding.svg?react";
import RecentIcon from "../../../assets/icons/navigation/recent.svg?react";
import SearchIcon from "../../../assets/icons/navigation/search.svg?react";
import SettingsIcon from "../../../assets/icons/navigation/settings.svg?react";
import Sidebar1Icon from "../../../assets/icons/navigation/sidebar1.svg?react";
import Sidebar2Icon from "../../../assets/icons/navigation/sidebar2.svg?react";
import SoftwareIcon from "../../../assets/icons/navigation/software.svg?react";
import TagsIcon from "../../../assets/icons/navigation/tags.svg?react";

import type { NavigationIconName } from "./icon-types";

const navigationIconMap: Record<NavigationIconName, (props: SVGProps<SVGSVGElement>) => JSX.Element> = {
  onboarding: OnboardingIcon,
  search: SearchIcon,
  files: FilesIcon,
  books: BooksIcon,
  software: SoftwareIcon,
  media: MediaIcon,
  games: GamesIcon,
  recent: RecentIcon,
  tags: TagsIcon,
  collections: CollectionsIcon,
  settings: SettingsIcon,
  connection: ConnectionIcon,
  close: CloseIcon,
  maxmize1: Maxmize1Icon,
  maxmize2: Maxmize2Icon,
  minimize: MinimizeIcon,
  sidebar1: Sidebar1Icon,
  sidebar2: Sidebar2Icon,
};

type SidebarIconProps = {
  name: NavigationIconName;
  className?: string;
};

export function SidebarIcon({ name, className }: SidebarIconProps) {
  const Icon = navigationIconMap[name];

  return <Icon aria-hidden="true" focusable="false" className={className} />;
}
