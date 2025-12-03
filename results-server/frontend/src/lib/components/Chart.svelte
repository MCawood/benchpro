<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as echarts from 'echarts';
  import type { TaskRunSummary } from '$lib/api/client';

  export let data: TaskRunSummary[] = [];
  export let type: 'line' | 'scatter' | 'bar' = 'scatter';

  let chartContainer: HTMLDivElement;
  let chart: echarts.ECharts | null = null;

  $: if (chart && data) {
    updateChart();
  }

  onMount(() => {
    chart = echarts.init(chartContainer, 'dark');
    updateChart();

    const resizeObserver = new ResizeObserver(() => {
      chart?.resize();
    });
    resizeObserver.observe(chartContainer);

    return () => {
      resizeObserver.disconnect();
    };
  });

  onDestroy(() => {
    chart?.dispose();
  });

  function updateChart() {
    if (!chart || !data.length) {
      chart?.setOption({
        title: {
          text: 'No data available',
          left: 'center',
          top: 'center',
          textStyle: { color: '#64748b', fontSize: 14 },
        },
      });
      return;
    }

    // Sort data by submit time
    const sortedData = [...data].sort(
      (a, b) => new Date(a.submit_time).getTime() - new Date(b.submit_time).getTime()
    );

    const dates = sortedData.map(d => new Date(d.submit_time).toLocaleDateString());
    const runtimes = sortedData.map(d => d.runtime_seconds ?? 0);
    const nodes = sortedData.map(d => d.node_count ?? 1);
    const labels = sortedData.map(d => d.label);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: type === 'scatter' ? 'item' : 'axis',
        backgroundColor: '#1e293b',
        borderColor: '#334155',
        textStyle: { color: '#f1f5f9' },
        formatter: (params: any) => {
          if (Array.isArray(params)) {
            const p = params[0];
            return `<div class="font-medium">${labels[p.dataIndex]}</div>
                    <div class="text-sm text-gray-400">Runtime: ${runtimes[p.dataIndex]?.toFixed(1)}s</div>
                    <div class="text-sm text-gray-400">Nodes: ${nodes[p.dataIndex]}</div>`;
          }
          return `<div class="font-medium">${labels[params.dataIndex]}</div>
                  <div class="text-sm text-gray-400">Runtime: ${params.value[1]?.toFixed(1)}s</div>
                  <div class="text-sm text-gray-400">Nodes: ${params.value[0]}</div>`;
        },
      },
      grid: {
        left: '60',
        right: '40',
        top: '40',
        bottom: '60',
      },
      xAxis: {
        type: type === 'scatter' ? 'value' : 'category',
        name: type === 'scatter' ? 'Node Count' : 'Submit Date',
        nameLocation: 'center',
        nameGap: 35,
        nameTextStyle: { color: '#94a3b8' },
        data: type !== 'scatter' ? dates : undefined,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } },
      },
      yAxis: {
        type: 'value',
        name: 'Runtime (seconds)',
        nameLocation: 'center',
        nameGap: 45,
        nameTextStyle: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } },
      },
      series: [
        {
          type: type,
          data: type === 'scatter'
            ? sortedData.map((d, i) => [nodes[i], runtimes[i]])
            : runtimes,
          symbolSize: type === 'scatter' ? 12 : 8,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#22c55e' },
              { offset: 1, color: '#16a34a' },
            ]),
          },
          lineStyle: type === 'line' ? { width: 2, color: '#22c55e' } : undefined,
          areaStyle: type === 'line' ? {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 197, 94, 0.3)' },
              { offset: 1, color: 'rgba(34, 197, 94, 0.05)' },
            ]),
          } : undefined,
          animationDuration: 1000,
          animationEasing: 'cubicOut',
        },
      ],
    };

    chart.setOption(option, true);
  }
</script>

<div bind:this={chartContainer} class="w-full h-96"></div>

