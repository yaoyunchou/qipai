import { RightOutlined } from "@ant-design/icons";
import { Button, DatePicker as AntDatePicker } from "antd";
import { ConfigProvider, DatePicker as MobileDatePicker } from "antd-mobile";
import zhCN from "antd-mobile/es/locales/zh-CN";
import dayjs, { type Dayjs } from "dayjs";
import { useState } from "react";

import "antd-mobile/es/global";

type OpenTimeInputProps = {
  value: Dayjs | null;
  onChange: (value: Dayjs | null) => void;
  isMobile: boolean;
};

export default function OpenTimeInput({ value, onChange, isMobile }: OpenTimeInputProps) {
  const [pickerVisible, setPickerVisible] = useState(false);

  if (!isMobile) {
    return (
      <AntDatePicker
        showTime={{ format: "HH:mm" }}
        format="YYYY-MM-DD HH:mm"
        value={value}
        onChange={onChange}
        style={{ width: "100%" }}
        showNow
        disabledDate={(current) => !!current && current > dayjs().endOf("day")}
      />
    );
  }

  return (
    <ConfigProvider locale={zhCN}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          type="button"
          onClick={() => setPickerVisible(true)}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
            height: 44,
            padding: "0 12px",
            border: "1px solid #d9d9d9",
            borderRadius: 6,
            background: "#fff",
            fontSize: 16,
            color: value ? "#000" : "#bfbfbf",
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <span>{value ? value.format("YYYY-MM-DD HH:mm") : "请选择开始时间"}</span>
          <RightOutlined style={{ color: "#999", fontSize: 12 }} />
        </button>
        <Button type="link" size="small" style={{ padding: 0, height: "auto" }} onClick={() => onChange(dayjs())}>
          设为当前时间
        </Button>
        <MobileDatePicker
          visible={pickerVisible}
          onClose={() => setPickerVisible(false)}
          precision="minute"
          title="选择开始时间"
          value={value?.toDate()}
          max={new Date()}
          onConfirm={(v) => {
            onChange(dayjs(v));
            setPickerVisible(false);
          }}
        />
      </div>
    </ConfigProvider>
  );
}
