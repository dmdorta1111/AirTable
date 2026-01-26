import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { DashboardBuilder } from '@/components/analytics/DashboardBuilder';
import { post } from '@/lib/api';

interface Widget {
  id: string;
  type: string;
  title: string;
  config?: Record<string, unknown>;
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface CreateDashboardRequest {
  name: string;
  description?: string;
  base_id?: string;
  layout_config: {
    widgets: Widget[];
  };
}

export const DashboardBuilderPage: React.FC = () => {
  const navigate = useNavigate();

  const createDashboardMutation = useMutation({
    mutationFn: async (data: CreateDashboardRequest) => {
      return post('/api/v1/dashboards', data);
    },
    onSuccess: () => {
      navigate('/dashboards');
    },
  });

  const handleSave = (widgets: Widget[]) => {
    createDashboardMutation.mutate({
      name: 'New Dashboard',
      description: 'Dashboard created with builder',
      layout_config: {
        widgets,
      },
    });
  };

  const handleCancel = () => {
    navigate('/dashboards');
  };

  return (
    <div className="h-screen">
      <DashboardBuilder onSave={handleSave} onCancel={handleCancel} />
    </div>
  );
};

export default DashboardBuilderPage;
