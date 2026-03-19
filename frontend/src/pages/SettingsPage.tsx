import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { promptTemplateApi } from '@/services/api';
import type { PromptTemplate, PromptTemplateUpdate } from '@/types';
import { Save, RotateCcw, Settings as SettingsIcon, FileText } from 'lucide-react';

const TEMPLATE_LABELS: Record<string, { label: string; description: string }> = {
  opening_template: {
    label: '开场白提示词',
    description: '主持人开场时使用的提示词，用于介绍会议主题和流程',
  },
  free_speak_template: {
    label: '自由发言邀请',
    description: '主持人邀请下一位参会者发言时的提示词',
  },
  guided_speak_template: {
    label: '引导发言提示词',
    description: '主持人针对特定发言人进行引导时的提示词',
  },
  participant_speak_template: {
    label: '参会者发言提示词',
    description: '发送给参会者邀请其发言的提示词',
  },
  round_summary_template: {
    label: '轮次摘要提示词',
    description: '每轮结束时主持人生成摘要的提示词',
  },
  closing_summary_template: {
    label: '会议总结提示词',
    description: '会议结束时主持人生成最终总结的提示词',
  },
};

const TEMPLATE_VARIABLES: Record<string, string[]> = {
  opening_template: ['meeting_title', 'meeting_type_label', 'meeting_description', 'max_rounds', 'participants_info', 'max_opening_words'],
  free_speak_template: ['meeting_title', 'round_number', 'max_rounds', 'previous_summaries', 'current_round_messages', 'speaker_name', 'speaker_role', 'speaker_expertise', 'previous_speaker_name'],
  guided_speak_template: ['meeting_title', 'round_number', 'max_rounds', 'current_topic', 'current_round_messages', 'speaker_name', 'speaker_role', 'speaker_expertise'],
  participant_speak_template: ['meeting_title', 'meeting_type_label', 'round_number', 'max_rounds', 'your_role', 'your_expertise', 'previous_summaries', 'current_round_messages', 'host_invitation', 'max_speak_words'],
  round_summary_template: ['meeting_title', 'round_number', 'round_messages', 'max_summary_words'],
  closing_summary_template: ['meeting_title', 'meeting_type_label', 'max_rounds', 'all_round_summaries'],
};

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [editForm, setEditForm] = useState<PromptTemplateUpdate>({});
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('opening_template');

  // Fetch templates
  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['prompt-templates'],
    queryFn: promptTemplateApi.list,
  });

  // Update template mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PromptTemplateUpdate }) =>
      promptTemplateApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt-templates'] });
      setIsEditDialogOpen(false);
      setSelectedTemplate(null);
      setEditForm({});
    },
  });

  const templates = templatesData?.items || [];
  const defaultTemplate = templates.find((t) => t.is_default);

  const handleEditTemplate = (template: PromptTemplate) => {
    setSelectedTemplate(template);
    setEditForm({
      name: template.name,
      opening_template: template.opening_template,
      round_summary_template: template.round_summary_template,
      guided_speak_template: template.guided_speak_template,
      free_speak_template: template.free_speak_template,
      closing_summary_template: template.closing_summary_template,
      participant_speak_template: template.participant_speak_template,
      max_opening_words: template.max_opening_words,
      max_summary_words: template.max_summary_words,
      max_speak_words: template.max_speak_words,
    });
    setIsEditDialogOpen(true);
  };

  const handleSave = () => {
    if (selectedTemplate) {
      updateMutation.mutate({ id: selectedTemplate.id, data: editForm });
    }
  };

  const handleReset = () => {
    if (selectedTemplate) {
      setEditForm({
        opening_template: selectedTemplate.opening_template,
        round_summary_template: selectedTemplate.round_summary_template,
        guided_speak_template: selectedTemplate.guided_speak_template,
        free_speak_template: selectedTemplate.free_speak_template,
        closing_summary_template: selectedTemplate.closing_summary_template,
        participant_speak_template: selectedTemplate.participant_speak_template,
        max_opening_words: selectedTemplate.max_opening_words,
        max_summary_words: selectedTemplate.max_summary_words,
        max_speak_words: selectedTemplate.max_speak_words,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">系统设置</h1>
          <p className="text-muted-foreground mt-1">管理会议流程提示词模板和系统配置</p>
        </div>
      </div>

      {/* Prompt Templates Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                提示词模板
              </CardTitle>
              <CardDescription>
                配置会议主持和进度推进的提示词模板
              </CardDescription>
            </div>
            {defaultTemplate && (
              <Button onClick={() => handleEditTemplate(defaultTemplate)}>
                <SettingsIcon className="h-4 w-4 mr-2" />
                编辑默认模板
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {templates.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              暂无模板，请先初始化默认模板
            </div>
          ) : (
            <div className="space-y-4">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 cursor-pointer"
                  onClick={() => handleEditTemplate(template)}
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="font-medium flex items-center gap-2">
                        {template.name}
                        {template.is_default && (
                          <Badge variant="secondary">默认</Badge>
                        )}
                        {template.is_system && (
                          <Badge variant="outline">系统</Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        代码: {template.code}
                      </div>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    更新于: {new Date(template.updated_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">开场白最大字数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{defaultTemplate?.max_opening_words || 200}</div>
            <p className="text-xs text-muted-foreground">主持开场白限制</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">摘要最大字数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{defaultTemplate?.max_summary_words || 300}</div>
            <p className="text-xs text-muted-foreground">轮次摘要限制</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">发言最大字数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{defaultTemplate?.max_speak_words || 300}</div>
            <p className="text-xs text-muted-foreground">参会者发言限制</p>
          </CardContent>
        </Card>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>编辑提示词模板</DialogTitle>
            <DialogDescription>
              修改会议流程的提示词模板。模板支持使用 {`{变量名}`} 格式的占位符。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid grid-cols-6 w-full">
                <TabsTrigger value="opening_template">开场</TabsTrigger>
                <TabsTrigger value="free_speak_template">邀请</TabsTrigger>
                <TabsTrigger value="guided_speak_template">引导</TabsTrigger>
                <TabsTrigger value="participant_speak_template">发言</TabsTrigger>
                <TabsTrigger value="round_summary_template">摘要</TabsTrigger>
                <TabsTrigger value="closing_summary_template">总结</TabsTrigger>
              </TabsList>

              {Object.entries(TEMPLATE_LABELS).map(([key, info]) => (
                <TabsContent key={key} value={key} className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor={key}>{info.label}</Label>
                      <div className="text-xs text-muted-foreground">
                        可用变量: {TEMPLATE_VARIABLES[key]?.join(', ')}
                      </div>
                    </div>
                    <Textarea
                      id={key}
                      placeholder={info.description}
                      value={(editForm as Record<string, string | number | undefined>)[key] as string || ''}
                      onChange={(e) =>
                        setEditForm({ ...editForm, [key]: e.target.value })
                      }
                      rows={12}
                      className="font-mono text-sm"
                    />
                  </div>
                </TabsContent>
              ))}
            </Tabs>

            {/* Word Limits */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="space-y-2">
                <Label htmlFor="max_opening_words">开场白最大字数</Label>
                <Input
                  id="max_opening_words"
                  type="number"
                  value={editForm.max_opening_words || 200}
                  onChange={(e) =>
                    setEditForm({ ...editForm, max_opening_words: parseInt(e.target.value) || 200 })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_summary_words">摘要最大字数</Label>
                <Input
                  id="max_summary_words"
                  type="number"
                  value={editForm.max_summary_words || 300}
                  onChange={(e) =>
                    setEditForm({ ...editForm, max_summary_words: parseInt(e.target.value) || 300 })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_speak_words">发言最大字数</Label>
                <Input
                  id="max_speak_words"
                  type="number"
                  value={editForm.max_speak_words || 300}
                  onChange={(e) =>
                    setEditForm({ ...editForm, max_speak_words: parseInt(e.target.value) || 300 })
                  }
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleReset}>
              <RotateCcw className="h-4 w-4 mr-2" />
              重置
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}