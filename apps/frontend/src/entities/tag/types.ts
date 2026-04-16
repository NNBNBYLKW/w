export type TagItemVM = {
  id: number;
  name: string;
};

export type TagResponseVM = {
  item: TagItemVM;
};

export type TagListResponseVM = {
  items: TagItemVM[];
};
