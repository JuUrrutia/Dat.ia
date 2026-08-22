import React, { useRef, useImperativeHandle, forwardRef } from 'react';
import ReactECharts from 'echarts-for-react';

export interface InteractiveChartRef {
  downloadImage: (filename?: string) => void;
  getEchartsInstance: () => any;
}

interface InteractiveChartProps {
  option: any;
  height?: string;
  className?: string;
}

export const InteractiveChart = forwardRef<InteractiveChartRef, InteractiveChartProps>(
  ({ option, height = '380px', className = '' }, ref) => {
    const chartRef = useRef<any>(null);

    useImperativeHandle(ref, () => ({
      downloadImage: (filename = 'grafico_datia.png') => {
        if (chartRef.current) {
          const echartInstance = chartRef.current.getEchartsInstance();
          if (echartInstance) {
            const base64 = echartInstance.getDataURL({
              type: 'png',
              pixelRatio: 2,
              backgroundColor: '#0B0F19',
            });
            const link = document.createElement('a');
            link.download = filename;
            link.href = base64;
            link.click();
          }
        }
      },
      getEchartsInstance: () => {
        return chartRef.current?.getEchartsInstance();
      },
    }));

    const finalOption = {
      backgroundColor: 'transparent',
      textStyle: {
        color: '#94A3B8',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      animationDuration: 600,
      animationEasing: 'cubicOut',
      ...option,
    };

    return (
      <div className={`w-full relative ${className}`}>
        <ReactECharts
          ref={chartRef}
          option={finalOption}
          style={{ height, width: '100%' }}
          opts={{ renderer: 'canvas' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    );
  }
);

InteractiveChart.displayName = 'InteractiveChart';
