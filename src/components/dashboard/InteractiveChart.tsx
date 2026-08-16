import React from 'react';
import ReactECharts from 'echarts-for-react';

interface InteractiveChartProps {
  option: any;
  height?: string;
}

export const InteractiveChart: React.FC<InteractiveChartProps> = ({ option, height = '360px' }) => {
  const defaultDarkThemeOption = {
    backgroundColor: 'transparent',
    textStyle: {
      color: '#9CA3AF',
      fontFamily: 'Inter, sans-serif'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1F2937',
      borderColor: '#374151',
      textStyle: { color: '#F9FAFB' },
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '12%',
      containLabel: true
    },
    ...option
  };

  return (
    <div className="w-full relative">
      <ReactECharts
        option={defaultDarkThemeOption}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'svg' }}
      />
    </div>
  );
};
