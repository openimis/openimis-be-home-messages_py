import graphene
from core import prefix_filterset, ExtendedConnection, filter_validity
from graphene_django import DjangoObjectType
from location.schema import HealthFacilityGQLType
from django.db.models import Q

from .models import Notice, NoticeAttachment


class NoticeGQLType(DjangoObjectType):
    attachment_count = graphene.Int()
    priority = graphene.String()
    legacy_id = graphene.Int()
    audit_user_id = graphene.Int()

    class Meta:
        model = Notice
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "legacy_id": ["exact", "isnull"],
            "uuid": ["exact"],
            "title": ["icontains"],
            "description": ["icontains"],
            "priority": ["exact"],
            "is_active": ["exact"],
            "schedule_publish": ["exact"],
            "publish_start_date": ["exact", "lt", "lte", "gt", "gte"],
            "created_at": ["exact", "lt", "lte", "gt", "gte"],
            "validity_from": ["exact", "lt", "lte", "gt", "gte"],
            "validity_to": ["exact", "isnull"],
            "audit_user_id": ["exact"],
            **prefix_filterset("health_facility__", HealthFacilityGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection 
    
    def resolve_attachment_count(self, info):
        return self.notice_attachments.filter(*filter_validity()).count()

    @classmethod
    def get_queryset(cls, queryset, info):
        """
        Default queryset filtering:
        1. Apply validity filter (validity_to__isnull=True), unless history is explicitly queried.
        2. Filter by user's health facility (row security):
           - Superusers / IMIS Admins can see all notices.
           - If notice has no health facility, everyone can see it.
           - If notice has a health facility, only users of that health facility can see it.
        """
        user = getattr(info.context, "user", None)
        from django.conf import settings

        # Validity filtering is handled by resolve_notices (supporting showHistory / legacyId).
        # Here we apply row security (health facility scoping) and ordering.
        if settings.ROW_SECURITY and user and not user.is_anonymous:
            i_user = getattr(user, "i_user", None) or getattr(user, "_u", None)
            is_admin = (
                getattr(user, "is_superuser", False)
                or getattr(user, "is_imis_admin", False)
                or (i_user and (getattr(i_user, "is_imis_admin", False) or getattr(i_user, "is_superuser", False)))
            )
            if not is_admin:
                hf_id = None
                if hasattr(user, 'health_facility') and user.health_facility:
                    hf_id = getattr(user.health_facility, 'id', None)
                elif hasattr(user, 'get_health_facility'):
                    hf = user.get_health_facility()
                    if hf:
                        hf_id = getattr(hf, 'id', None)
                if not hf_id and i_user:
                    hf_id = getattr(i_user, 'health_facility_id', None)

                q_filter = Q(health_facility__isnull=True)
                if hf_id:
                    q_filter |= Q(health_facility_id=hf_id)
                queryset = queryset.filter(q_filter)
        elif settings.ROW_SECURITY and (not user or user.is_anonymous):
            return queryset.none()

        return queryset.order_by('-created_at')

class NoticeAttachmentGQLType(DjangoObjectType):
    doc = graphene.String(source='document')
    class Meta:
        model = NoticeAttachment
        interfaces = (graphene.relay.Node,)
        fields = '__all__'
        filter_fields = {
            "id": ["exact"],
            "general_type": ["exact", "icontains"],
            "type": ["exact", "icontains"],
            "title": ["exact", "icontains"],
            "date": ["exact", "lt", "lte", "gt", "gte"],
            "filename": ["exact", "icontains"],
            "mime": ["exact", "icontains"],
            "url": ["exact", "icontains"],
            **prefix_filterset("notice__", NoticeGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection

