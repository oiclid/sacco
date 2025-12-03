from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Member
from .serializers import MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    lookup_field = "registration_number"

    @action(detail=True, methods=['post'])
    def shutdown(self, request, registration_number=None):
        """
        POST /members/<reg_no>/shutdown/
        { "reason": "quit"|"retired"|"deceased" }
        """
        member = self.get_object()
        reason = request.data.get("reason")

        if not reason:
            return Response({"error": "reason is required"}, status=400)

        try:
            member.shutdown(reason)
            return Response(MemberSerializer(member).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
