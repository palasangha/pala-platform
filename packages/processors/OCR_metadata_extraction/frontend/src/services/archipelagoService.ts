import api from './api';
import { useAuthStore } from '@/stores/authStore';

const getHeaders = () => {
  const token = useAuthStore.getState().accessToken;
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
};

export const archipelagoAPI = {
  updateMetadata: async (nodeUuid: string, metadata: string): Promise<any> => {
    const headers = { ...getHeaders(), 'Content-Type': 'application/json' };
    const { data } = await api.put(`/archipelago/node/${nodeUuid}/metadata`, metadata, { headers });
    return data;
  },
};
