import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Card, Button, Typography, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import DraggableCourse from './DraggableCourse';

const { Text } = Typography;

function DroppableSemester({ id, semester, year, courses, onAddCourse, onRemoveCourse, validation }) {
  const { setNodeRef, isOver } = useDroppable({ id });

  // Calculate semester complexity
  const semesterComplexity = validation?.semester_complexities?.[`Year ${year} ${semester}`] || 0;
  const complexityColor = semesterComplexity > 60 ? '#ff4d4f' : semesterComplexity > 45 ? '#faad14' : '#52c41a';

  return (
    <div
      ref={setNodeRef}
      style={{
        padding: '16px',
        minHeight: '200px',
        background: isOver ? '#e6f7ff' : '#fafafa',
        border: isOver ? '2px dashed #1890ff' : '1px solid #d9d9d9',
        borderRight: semester === 'Fall' ? 'none' : '1px solid #d9d9d9',
        transition: 'all 0.2s'
      }}
    >
      <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text strong>{semester} {year}</Text>
        <Text style={{ fontSize: '12px', color: complexityColor }}>
          Complexity: {semesterComplexity}
        </Text>
      </div>

      <SortableContext
        items={courses}
        strategy={verticalListSortingStrategy}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {courses.map(courseId => (
            <DraggableCourse
              key={courseId}
              id={courseId}
              onRemove={() => onRemoveCourse(courseId)}
              validation={validation}
            />
          ))}
        </Space>
      </SortableContext>

      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={onAddCourse}
        style={{ width: '100%', marginTop: '8px' }}
        size="small"
      >
        Add Course
      </Button>
    </div>
  );
}

export default DroppableSemester;
