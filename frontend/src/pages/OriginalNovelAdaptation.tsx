import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Space,
  Spin,
  Tag,
  Typography,
  Upload,
} from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { BookOutlined, FileTextOutlined, RocketOutlined, UploadOutlined } from '@ant-design/icons';

import { adaptationApi } from '../services/api';
import type {
  AdaptationBatchItem,
  AdaptationCanonAudit,
  AdaptationProjectDetail,
  AdaptationProjectListItem,
} from '../types';

const { Paragraph, Text, Title } = Typography;
const { TextArea } = Input;

const BRIEF_EXAMPLES = [
  {
    label: '12岁适读',
    text: '请按时间顺序改编，语言尽量清楚自然，适合12岁左右读者阅读。不要改变原著关键情节、人物关系、世界观和结局走向，减少露骨情爱描写，但保留事件结果。',
  },
  {
    label: '更口语一些',
    text: '请保留原著核心剧情和结果，用更容易理解的中文重写，句子不要太绕，章节推进清晰，适合青少年连续阅读。',
  },
  {
    label: '强化叙事清晰度',
    text: '请按时间顺序重新规划章节，让每一章的事件目标更清晰，减少重复抒情和过长铺陈，但不要删改关键事件结果。',
  },
];

const STATUS_TEXT: Record<string, string> = {
  source_uploaded: '已导入原著',
  brief_saved: '已保存提示词',
  batch_planning: '正在规划',
  batch_draft_ready: '待确认批次',
  batch_confirmed: '批次已确认',
  batch_generating: '正在生成正文',
  batch_written: '已写出正文',
};

export default function OriginalNovelAdaptation() {
  const navigate = useNavigate();
  const isMobile = window.innerWidth <= 768;
  const [projects, setProjects] = useState<AdaptationProjectListItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdaptationProjectDetail | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createFile, setCreateFile] = useState<File | null>(null);
  const [briefText, setBriefText] = useState('');
  const [savingBrief, setSavingBrief] = useState(false);
  const [batchSize, setBatchSize] = useState(4);
  const [planning, setPlanning] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [generatingItemId, setGeneratingItemId] = useState<string | null>(null);

  const loadProjects = async (preferredId?: string) => {
    try {
      setLoadingList(true);
      const list = await adaptationApi.listProjects();
      setProjects(list);
      const nextSelected = preferredId || selectedProjectId || list[0]?.adaptation_project_id || null;
      setSelectedProjectId(nextSelected);
    } catch (error) {
      console.error('加载原著改编项目失败:', error);
    } finally {
      setLoadingList(false);
    }
  };

  const loadDetail = async (adaptationProjectId: string) => {
    try {
      setLoadingDetail(true);
      const result = await adaptationApi.getProjectDetail(adaptationProjectId);
      setDetail(result);
      setBriefText(result.active_brief_text || '');
    } catch (error) {
      console.error('加载原著改编详情失败:', error);
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    void loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setDetail(null);
      return;
    }
    void loadDetail(selectedProjectId);
  }, [selectedProjectId]);

  const handleCreate = async () => {
    if (!createFile) {
      message.warning('请先选择原著 TXT 文件');
      return;
    }
    try {
      setCreating(true);
      const created = await adaptationApi.createProject({
        file: createFile,
        title: createTitle || undefined,
        description: createDescription || undefined,
      });
      message.success('原著改编项目已创建');
      setCreateVisible(false);
      setCreateTitle('');
      setCreateDescription('');
      setCreateFile(null);
      await loadProjects(created.adaptation_project_id);
    } catch (error) {
      console.error('创建原著改编项目失败:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleSaveBrief = async () => {
    if (!detail || !briefText.trim()) {
      message.warning('请先填写自由提示词');
      return;
    }
    try {
      setSavingBrief(true);
      await adaptationApi.saveBrief(detail.adaptation_project_id, { brief_text: briefText.trim() });
      message.success('提示词已保存');
      await loadDetail(detail.adaptation_project_id);
      await loadProjects(detail.adaptation_project_id);
    } catch (error) {
      console.error('保存提示词失败:', error);
    } finally {
      setSavingBrief(false);
    }
  };

  const handlePlanBatch = async () => {
    if (!detail) return;
    if (!detail.active_brief_text && !briefText.trim()) {
      message.warning('请先保存自由提示词');
      return;
    }
    try {
      setPlanning(true);
      await adaptationApi.planNextBatch(detail.adaptation_project_id, batchSize);
      message.success('下一批章节已生成，请先确认');
      await loadDetail(detail.adaptation_project_id);
      await loadProjects(detail.adaptation_project_id);
    } catch (error) {
      console.error('规划下一批失败:', error);
    } finally {
      setPlanning(false);
    }
  };

  const handleConfirmBatch = async () => {
    if (!detail?.draft_batch) return;
    try {
      setConfirming(true);
      const result = await adaptationApi.confirmBatch(detail.adaptation_project_id, detail.draft_batch.id);
      message.success(`已确认并物化 ${result.materialized_count} 章`);
      await loadDetail(detail.adaptation_project_id);
      await loadProjects(detail.adaptation_project_id);
    } catch (error) {
      console.error('确认批次失败:', error);
    } finally {
      setConfirming(false);
    }
  };

  const handleGenerateChapter = async (item: AdaptationBatchItem, regenerate = false) => {
    if (!detail || !item.materialized_chapter_id) {
      message.warning('请先确认批次后再生成正文');
      return;
    }
    try {
      setGeneratingItemId(item.id);
      const result = await adaptationApi.generateChapter(detail.adaptation_project_id, {
        chapter_id: item.materialized_chapter_id,
        batch_item_id: item.id,
        regenerate,
      });
      message.success(`《${result.title}》正文已生成`);
      await loadDetail(detail.adaptation_project_id);
    } catch (error) {
      console.error('生成正文失败:', error);
    } finally {
      setGeneratingItemId(null);
    }
  };

  const currentDraftItems = detail?.draft_batch?.items || [];
  const latestConfirmedBatch = detail?.confirmed_batches?.[detail.confirmed_batches.length - 1] || null;
  const canEditBrief = detail?.can_edit_brief ?? true;

  const auditCards = useMemo(() => {
    return (detail?.recent_audits || []).map((audit: AdaptationCanonAudit) => (
      <Card key={audit.id} size="small" style={{ marginBottom: 12 }}>
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <Space wrap>
            <Tag color={audit.audit_type === 'planning' ? 'blue' : 'green'}>
              {audit.audit_type === 'planning' ? '规划审计' : '正文审计'}
            </Tag>
            {audit.brief_version ? <Tag>提示词 v{audit.brief_version}</Tag> : null}
            <Text type="secondary">{new Date(audit.created_at).toLocaleString('zh-CN')}</Text>
          </Space>
          <Text>{audit.summary || '无摘要'}</Text>
          <Text type="secondary">切块：{audit.retrieved_chunk_ids.join(', ') || '无'}</Text>
          <Space wrap>
            {Object.entries(audit.contradiction_results || {}).map(([key, value]) => (
              <Tag key={key} color={value?.status === 'pass' ? 'success' : value?.status === 'fail' ? 'error' : 'warning'}>
                {key}: {value?.status || 'warn'}
              </Tag>
            ))}
          </Space>
        </Space>
      </Card>
    ));
  }, [detail?.recent_audits]);

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card>
          <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
            <div>
              <Title level={4} style={{ marginTop: 0 }}>原著改编</Title>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                上传整本原著，填写一段自由提示词，然后按批次规划新章节。每一批都要先确认，才会写入现有大纲和章节。
              </Paragraph>
            </div>
            <Button type="primary" icon={<UploadOutlined />} onClick={() => setCreateVisible(true)}>
              新建改编项目
            </Button>
          </Space>
        </Card>

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '320px minmax(0, 1fr)', gap: 16 }}>
          <Card title="改编项目" loading={loadingList}>
            {projects.length === 0 ? (
              <Empty description="还没有原著改编项目" />
            ) : (
              <List
                dataSource={projects}
                renderItem={(item) => (
                  <List.Item
                    onClick={() => setSelectedProjectId(item.adaptation_project_id)}
                    style={{
                      cursor: 'pointer',
                      borderRadius: 8,
                      padding: 12,
                      marginBottom: 8,
                      background: selectedProjectId === item.adaptation_project_id ? '#f0f7ff' : undefined,
                      border: selectedProjectId === item.adaptation_project_id ? '1px solid #91caff' : '1px solid #f0f0f0',
                    }}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Text strong>{item.title}</Text>
                      <Text type="secondary">{item.source_filename}</Text>
                      <Space wrap>
                        <Tag color="blue">{STATUS_TEXT[item.workflow_status] || item.workflow_status}</Tag>
                        <Tag>已确认 {item.confirmed_batch_count} 批</Tag>
                        <Tag>最新批次 {item.latest_batch_number}</Tag>
                      </Space>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>

          <Spin spinning={loadingDetail}>
            {!detail ? (
              <Card><Empty description="选择一个项目开始操作" /></Card>
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Card
                  title={
                    <Space>
                      <BookOutlined />
                      <span>{detail.title}</span>
                      <Tag color="blue">{STATUS_TEXT[detail.workflow_status] || detail.workflow_status}</Tag>
                    </Space>
                  }
                  extra={
                    <Button onClick={() => navigate(`/project/${detail.project_id}/chapters`)}>
                      去章节页
                    </Button>
                  }
                >
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Text type="secondary">原著文件：{detail.source_filename}</Text>
                    <Text type="secondary">全文字符：{detail.total_characters}，切块：{detail.total_chunks}</Text>
                    <Alert
                      type="info"
                      showIcon
                      message="当前流程不会一次生成全书，也不会按原章节原封不动导入。每次只规划下一批，并且要先确认，之后才能继续往下。"
                    />
                  </Space>
                </Card>

                <Card title="自由提示词">
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <TextArea
                      rows={8}
                      value={briefText}
                      disabled={!canEditBrief}
                      onChange={(event) => setBriefText(event.target.value)}
                      placeholder="例如：按时间顺序，适合12岁阅读，语言更清楚，不改变原著情节结果……"
                    />
                    <Space wrap>
                      {BRIEF_EXAMPLES.map((example) => (
                        <Button key={example.label} size="small" onClick={() => setBriefText(example.text)} disabled={!canEditBrief}>
                          {example.label}
                        </Button>
                      ))}
                    </Space>
                    <Space>
                      <Button type="primary" onClick={handleSaveBrief} loading={savingBrief} disabled={!canEditBrief}>
                        保存提示词
                      </Button>
                      {detail.active_brief_version ? <Tag>当前版本 v{detail.active_brief_version}</Tag> : null}
                    </Space>
                  </Space>
                </Card>

                <Card title="下一批规划">
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <Space wrap>
                      <Text>本次生成章节数</Text>
                      <InputNumber min={1} max={20} value={batchSize} onChange={(value) => setBatchSize(value || 4)} />
                      <Button
                        type="primary"
                        icon={<RocketOutlined />}
                        onClick={handlePlanBatch}
                        loading={planning}
                        disabled={!detail.can_plan_next_batch}
                      >
                        规划下一批章节
                      </Button>
                    </Space>
                    {!detail.can_plan_next_batch ? (
                      <Alert type="warning" showIcon message="当前有未确认草稿批次，请先确认后再继续规划。" />
                    ) : null}
                  </Space>
                </Card>

                <Card
                  title="当前草稿批次"
                  extra={
                    detail.draft_batch ? (
                      <Button type="primary" onClick={handleConfirmBatch} loading={confirming}>
                        确认这一批并写入大纲/章节
                      </Button>
                    ) : null
                  }
                >
                  {!detail.draft_batch ? (
                    <Empty description="还没有待确认批次" />
                  ) : (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <Alert
                        type="warning"
                        showIcon
                        message="确认前不会写入共享大纲和章节表。确认后，才会在现有项目里创建对应的大纲和空章节。"
                      />
                      <Text strong>批次摘要：{detail.draft_batch.batch_summary || '无'}</Text>
                      <List
                        dataSource={currentDraftItems}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={6} style={{ width: '100%' }}>
                              <Space wrap>
                                <Tag>第 {item.item_index} 章</Tag>
                                <Text strong>{item.proposed_title}</Text>
                              </Space>
                              <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                                {item.proposed_outline}
                              </Paragraph>
                              <Text type="secondary">切块：{item.source_chunk_ids.join(', ')}</Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  )}
                </Card>

                <Card title="最近已确认批次">
                  {detail.confirmed_batches.length === 0 ? (
                    <Empty description="还没有确认过的批次" />
                  ) : (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      {detail.confirmed_batches.map((batch) => (
                        <Card
                          key={batch.id}
                          size="small"
                          title={`第 ${batch.batch_number} 批`}
                          extra={<Tag color="success">已确认</Tag>}
                        >
                          <Space direction="vertical" size={10} style={{ width: '100%' }}>
                            <Text>{batch.batch_summary || '无摘要'}</Text>
                            <List
                              dataSource={batch.items}
                              renderItem={(item) => (
                                <List.Item
                                  actions={[
                                    item.materialized_chapter_id ? (
                                      <Button
                                        key="generate"
                                        icon={<FileTextOutlined />}
                                        loading={generatingItemId === item.id}
                                        onClick={() => void handleGenerateChapter(item, false)}
                                      >
                                        生成正文
                                      </Button>
                                    ) : null,
                                    item.materialized_chapter_id ? (
                                      <Button
                                        key="regenerate"
                                        loading={generatingItemId === item.id}
                                        onClick={() => void handleGenerateChapter(item, true)}
                                      >
                                        重新生成
                                      </Button>
                                    ) : null,
                                    item.materialized_chapter_id ? (
                                      <Button
                                        key="open"
                                        onClick={() => navigate(`/project/${detail.project_id}/chapters`)}
                                      >
                                        查看章节
                                      </Button>
                                    ) : null,
                                  ].filter(Boolean)}
                                >
                                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                    <Text strong>{item.proposed_title}</Text>
                                    <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                                      {item.proposed_outline}
                                    </Paragraph>
                                  </Space>
                                </List.Item>
                              )}
                            />
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  )}
                </Card>

                <Card title="审计记录">
                  {auditCards.length === 0 ? <Empty description="还没有审计记录" /> : auditCards}
                </Card>

                {latestConfirmedBatch ? (
                  <Alert
                    type="success"
                    showIcon
                    message={`最近一次已确认批次是第 ${latestConfirmedBatch.batch_number} 批。后续继续规划时，会带上原著切块、最新提示词、已确认批次和已写正文一起作为上下文。`}
                  />
                ) : null}
              </Space>
            )}
          </Spin>
        </div>
      </Space>

      <Modal
        open={createVisible}
        onCancel={() => {
          setCreateVisible(false);
          setCreateFile(null);
        }}
        onOk={() => void handleCreate()}
        okText="创建"
        confirmLoading={creating}
        title="新建原著改编项目"
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Input
            value={createTitle}
            onChange={(event) => setCreateTitle(event.target.value)}
            placeholder="项目标题，可留空自动用文件名"
          />
          <TextArea
            rows={3}
            value={createDescription}
            onChange={(event) => setCreateDescription(event.target.value)}
            placeholder="项目说明，可选"
          />
          <Upload
            beforeUpload={(file) => {
              setCreateFile(file);
              return false;
            }}
            fileList={createFile ? ([{ uid: createFile.name, name: createFile.name, status: 'done' }] as UploadFile[]) : []}
            onRemove={() => {
              setCreateFile(null);
              return true;
            }}
            accept=".txt"
            maxCount={1}
          >
            <Button icon={<UploadOutlined />}>选择原著 TXT</Button>
          </Upload>
          <Text type="secondary">这一版只支持整本 TXT 原著导入，后续章节规划按批次推进。</Text>
        </Space>
      </Modal>
    </div>
  );
}
