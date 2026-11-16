import { Segmented } from "antd";

export type DirectionTone = "blue" | "red";

export type DirectionOption = {
  label: string;
  value: string;
  tone: DirectionTone;
};

/**
 * 借钱/还钱、输/赢这类二选一开关。
 * 选中项的底色跟随该选项的颜色：蓝或红。
 */
export default function DirectionSwitch({
  value,
  onChange,
  options,
}: {
  value?: string;
  onChange?: (value: string) => void;
  options: DirectionOption[];
}) {
  const current = value ?? options[0]?.value;
  const tone = options.find((item) => item.value === current)?.tone ?? "blue";

  return (
    <Segmented
      className={`direction-switch direction-switch-${tone}`}
      value={value}
      onChange={(next) => onChange?.(String(next))}
      options={options.map((item) => ({
        value: item.value,
        label: (
          <span className={`direction-label direction-label-${item.tone}`}>{item.label}</span>
        ),
      }))}
    />
  );
}
